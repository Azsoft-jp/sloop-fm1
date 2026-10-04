/* SPDX-License-Identifier: GPL-3.0-only */
/* Synthesised drum kits (drums.c kits DRUM_SAMPLED..): analogue-style models in fixed
 * point, in the spirit of the classic drum machines and the PO-32. Every sound of a kit
 * is one dsnd_t (tools/gen_drumkits.py writes the kits into felucca_drumkits.h):
 *   tone   SINE / TRI / SQUARE / FM / BELL (two squares 1 : 1.48) with an exponential
 *          pitch drop (BEND semitones, over BTIME) and its own decay
 *   noise  WHITE / METAL (six squares at the 808 cymbal ratios) / CYM (metal + white) /
 *          CHIP (15-bit LFSR, clocked by LPF) with its own decay; CLAP: 3 bursts, then the tail
 *   filter one-pole low-pass, two one-pole high-passes (on the noise; BELL: on the tone too)
 *   drive  tanh; the kit's crush: bit depth and sample-and-hold
 * Costs ~40 integer ops per voice and sample (METAL: +6 adds); envelopes and the pitch
 * run at the control rate (CTL) and are ramped per sample. */
enum { DW_NONE, DW_SINE, DW_TRI, DW_SQUARE, DW_FM, DW_BELL };
enum { DN_NONE, DN_WHITE, DN_METAL, DN_CYM, DN_CHIP, DN_CLAP = 0x10 };
typedef struct {
    uint8_t wave, src;           /* DW_*, DN_* (| DN_CLAP) */
    uint8_t pitch;               /* MIDI note of the tone (METAL / CYM: their base) */
    uint8_t bend, btime;         /* pitch drop: semitones at the hit, DECAY_K index of its fall */
    uint8_t decay, tlev;         /* tone: DECAY_K index, level 0..127 */
    uint8_t nlev, ndec;          /* noise: level 0..127, DECAY_K index */
    uint8_t lpf, hpf;            /* CUTOFF_HZ index; lpf 127 / hpf 0 = off; CHIP: lpf = clock */
    uint8_t drive;               /* 0..127 */
} dsnd_t;
#define DS_LANES 14              /* the synthesised sounds (DS_NOTE): kick .. cowbell, clave */
typedef struct {
    const char *name, *style;
    uint8_t crush;               /* low nibble: bits dropped, high nibble: sample-and-hold - 1 */
    dsnd_t s[DS_LANES];
} dkit_t;
#include "felucca_drumkits.h"    /* DS_KITS[], DS_NKITS (tools/gen_drumkits.py) */

/* GM note -> synth lane (low nibble + 16 * ...) and a pitch offset in semitones */
static const struct { uint8_t lane; int8_t semi; } DS_MAP[128 - 35] = {
    /* 35 */ {0, -2}, {0, 0}, {11, 0}, {1, 0}, {2, 0}, {1, 1}, {5, -3}, {3, 0}, {5, 0}, {3, -1},
    /* 45 */ {5, 3}, {4, 0}, {6, -3}, {6, 0}, {7, 0}, {6, 3}, {8, 0}, {7, 3}, {8, 6}, {9, 4},
    /* 55 */ {7, 5}, {12, 0}, {7, 1}, {9, -5}, {8, 1}, {10, 9}, {10, 6}, {10, 3}, {10, 0}, {10, -5},
    /* 65 */ {6, 5}, {6, 1}, {12, 7}, {12, 3}, {9, -3}, {9, 0}, {13, 9}, {13, 6}, {9, -7}, {9, -9},
    /* 75 */ {13, 0}, {13, 4}, {13, -1}, {10, 12}, {10, 8}, {8, 24}, {8, 20}, {9, 2},
    /* 83..127: shaker */
};
static uint32_t ds_lane(uint32_t note, int32_t *semi)
{
    *semi = 0;
    if (note < 35u)
        return 0;
    if (note >= 83u)
        return 9;
    *semi = DS_MAP[note - 35u].semi;
    return DS_MAP[note - 35u].lane;
}

typedef struct {
    const dsnd_t *d;
    uint32_t ph, inc, inc_to;    /* tone phase; increment now and at the end of the block */
    uint32_t ph2, mph[6];        /* BELL / FM second oscillator, the six metal squares */
    uint32_t minc[6];
    int32_t pe;                  /* pitch envelope Q15 (32767 = BEND semitones) */
    int32_t amp, amp_to;         /* tone envelope Q15, now and at the end of the block */
    int32_t nz, nz_to;           /* noise envelope Q15 */
    uint32_t kpe, ka, kn;        /* per-block decay factors Q16 */
    uint32_t t;                  /* samples since the hit (CLAP bursts) */
    int32_t base16;              /* pitch in 1/16 semitones */
    int32_t lp, hp1, hp2, hpx1, hpx2;   /* filter states */
    int32_t alp, ahp;            /* one-pole coefficients Q15, 0 = off */
    int32_t rnd;                 /* white noise state */
    uint32_t lfsr, cacc, cinc;   /* CHIP noise */
    int32_t cval;
    int32_t gain;                /* velocity Q15 */
    int32_t held, holdn;         /* crush: sample-and-hold */
    uint8_t crush, bursts;
} dsv_t;

/* per-sample DECAY_K (Q16) -> per-block (CTL = 32 samples) by squaring five times */
static uint32_t ds_k32(uint32_t idx)
{
    uint32_t k = DECAY_K[idx & 127u], i;
    for (i = 0; i < 5u; i++)
        k = (k * k) >> 16;
    return k;
}
static int32_t ds_onepole(uint32_t cut)                 /* CUTOFF_HZ index -> a = g / (1 + g), Q15 */
{
    uint32_t g = SVF_G[cut & 127u];
    return (int32_t)((g << 15) / (4096u + g));
}
static uint32_t ds_inc(int32_t p16) { return PITCH_INC[clamp(p16, 0, 127 * 16 + 15)]; }

/* the 808 cymbal oscillators (205.3 304.4 369.6 522.7 540 800 Hz) as 1/16 semitones above the first */
static const int16_t DS_METAL[6] = {0, 109, 163, 259, 268, 377};

static void ds_on(dsv_t *s, const dkit_t *kit, uint32_t note, uint32_t vel)
{
    int32_t semi;
    uint32_t lane = ds_lane(note, &semi), i;
    const dsnd_t *d = &kit->s[lane];
    memset(s, 0, sizeof *s);
    s->d = d;
    s->crush = kit->crush;
    s->gain = (int32_t)vel * 258;
    s->base16 = ((int32_t)d->pitch + semi) * 16;
    s->pe = d->bend ? 32767 : 0;
    s->kpe = ds_k32(d->btime);
    s->inc = s->inc_to = ds_inc(s->base16 + ((s->pe * (int32_t)d->bend * 16) >> 15));
    s->amp = s->amp_to = d->wave ? (int32_t)d->tlev * 258 : 0;
    s->ka = ds_k32(d->decay);
    s->nz = s->nz_to = (d->src & 15u) ? (int32_t)d->nlev * 258 : 0;
    s->kn = (d->src & DN_CLAP) ? ds_k32(12) : ds_k32(d->ndec);  /* CLAP: short bursts first */
    s->bursts = 1;
    s->alp = d->lpf < 127u && (d->src & 15u) != DN_CHIP ? ds_onepole(d->lpf) : 0;
    s->ahp = d->hpf ? ds_onepole(d->hpf) : 0;
    s->rnd = (int32_t)(0x9E3779B9u ^ (note * 2654435761u) ^ rng());
    s->lfsr = 0x4001u;
    {   /* CHIP clock: 8x that note; saturated (the top notes would wrap 32 bits: a dull noise) */
        uint32_t ci = PITCH_INC[clamp((int32_t)d->lpf, 0, 127) * 16];
        s->cinc = ci >= 0x20000000u ? 0xFFFFFFFFu : ci << 3;
    }
    for (i = 0; i < 6u; i++)
        s->minc[i] = ds_inc(s->base16 + DS_METAL[i]);
}

/* one CTL block of control: the envelopes' targets at its end */
static void ds_control(dsv_t *s)
{
    const dsnd_t *d = s->d;
    s->amp = s->amp_to;
    s->nz = s->nz_to;
    s->inc = s->inc_to;
    s->amp_to = (int32_t)(((uint32_t)s->amp * s->ka) >> 16);
    if ((d->src & DN_CLAP) && s->bursts < 4u && s->t >= s->bursts * 400u) {
        s->nz = (int32_t)d->nlev * 258;                 /* bursts at 0, 9, 18 ms; the 4th is the tail */
        if (++s->bursts == 4u)
            s->kn = ds_k32(d->ndec);
    }
    s->nz_to = (int32_t)(((uint32_t)s->nz * s->kn) >> 16);
    s->pe = (int32_t)(((uint32_t)s->pe * s->kpe) >> 16);
    s->inc_to = ds_inc(s->base16 + ((s->pe * (int32_t)d->bend * 16) >> 15));
}

static int ds_alive(const dsv_t *s)
{
    if ((s->d->src & DN_CLAP) && s->bursts < 4u)
        return 1;                                       /* bursts still to come */
    return s->amp > 8 || s->amp_to > 8 || s->nz > 8 || s->nz_to > 8;
}

/* n (<= CTL) samples of voice s into out[] (Q15-ish, peak ~ 32767); returns 0 when it ended */
static int ds_render(dsv_t *s, int32_t *out, uint32_t n)
{
    const dsnd_t *d = s->d;
    uint32_t i, src = d->src & 15u, wave = d->wave;
    int32_t da = (s->amp_to - s->amp) >> CTL_LOG2, dn = (s->nz_to - s->nz) >> CTL_LOG2;   /* (no divide) */
    int32_t di = (int32_t)(s->inc_to - s->inc) >> CTL_LOG2;
    int32_t a = s->amp, z = s->nz, inc = (int32_t)s->inc;
    int32_t drive = 16 + d->drive, bits = s->crush & 15, hold = (s->crush >> 4) + 1;
    for (i = 0; i < n; i++) {
        int32_t tone = 0, nz = 0, x;
        if (wave) {
            switch (wave) {
            case DW_SINE: tone = sine_i(s->ph); break;
            case DW_TRI: tone = osc_tri(s->ph); break;
            case DW_SQUARE: tone = (int32_t)s->ph < 0 ? -24000 : 24000; break;
            case DW_FM:                                 /* ratio 1.41: metallic, index follows the tone */
                tone = sine_i(s->ph + ((uint32_t)(sine_i(s->ph2) * a) << 1));
                s->ph2 += (uint32_t)inc + ((uint32_t)inc >> 2) + ((uint32_t)inc >> 3) + ((uint32_t)inc >> 5);
                break;
            default:                                    /* BELL: two squares */
                tone = ((int32_t)s->ph < 0 ? -12000 : 12000) + ((int32_t)s->ph2 < 0 ? -12000 : 12000);
                s->ph2 += (uint32_t)inc + ((uint32_t)inc >> 1) - ((uint32_t)inc >> 6);
                break;
            }
            s->ph += (uint32_t)inc;
            tone = mulq15(tone, a);
        }
        if (src) {
            if (src == DN_WHITE) {
                nz = (int32_t)noise32(&s->rnd) >> 17;
            } else if (src == DN_CHIP) {
                s->cacc += s->cinc;
                if (s->cacc < s->cinc) {                /* wrapped: clock the LFSR */
                    uint32_t b = (s->lfsr ^ (s->lfsr >> 1)) & 1u;
                    s->lfsr = (s->lfsr >> 1) | (b << 14);
                }
                nz = (s->lfsr & 1u) ? 20000 : -20000;
            } else {                                    /* METAL / CYM: six squares (+ white) */
                s->mph[0] += s->minc[0];              /* unrolled: one sign bit each */
                s->mph[1] += s->minc[1];
                s->mph[2] += s->minc[2];
                s->mph[3] += s->minc[3];
                s->mph[4] += s->minc[4];
                s->mph[5] += s->minc[5];
                nz = (int32_t)(((s->mph[0] >> 31) + (s->mph[1] >> 31) + (s->mph[2] >> 31) +
                                (s->mph[3] >> 31) + (s->mph[4] >> 31) + (s->mph[5] >> 31)) * 9600u) - 28800;
                if (src == DN_CYM)
                    nz += (int32_t)noise32(&s->rnd) >> 18;
            }
            if (wave == DW_BELL)
                nz += tone, tone = 0;
            if (s->alp) {
                s->lp += mulq15(nz - s->lp, s->alp);
                nz = s->lp;
            }
            if (s->ahp) {                               /* two one-pole high-passes: 12 dB / oct */
                s->hp1 += mulq15(nz - s->hp1, s->ahp);
                nz -= s->hp1;
                s->hp2 += mulq15(nz - s->hp2, s->ahp);
                nz -= s->hp2;
            }
            nz = mulq15(nz, z);
            if (d->src & DN_CLAP)
                nz <<= 1;                               /* band-passed: as loud as the others */
        } else if (wave == DW_BELL && (s->alp || s->ahp)) {
            x = tone;
            if (s->alp) { s->lp += mulq15(x - s->lp, s->alp); x = s->lp; }
            if (s->ahp) { s->hp1 += mulq15(x - s->hp1, s->ahp); x -= s->hp1; }
            tone = x;
        }
        x = tone + nz;
        if (d->drive)
            x = softclip((x * drive) >> 4);
        if (s->crush) {
            if (--s->holdn <= 0) {
                s->holdn = hold;
                s->held = (x >> bits) << bits;
            }
            x = s->held;
        }
        out[i] = mulq15(x, s->gain);
        a += da;
        z += dn;
        inc += di;
    }
    s->t += n;
    ds_control(s);
    return ds_alive(s);
}
