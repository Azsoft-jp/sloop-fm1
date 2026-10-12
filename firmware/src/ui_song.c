/* SPDX-License-Identifier: GPL-3.0-only */
/* Compact 240 x 240 song-order editor. All changes and flash saves require
 * stopped transport. The four existing project slots are sections A..D. */
static uint8_t song_cursor, song_store_armed, song_load_armed;
static uint32_t song_store_deadline;
static int on_song_page(void) { return !ui.home && cur_page()->scope == SC_SONG; }
static void song_sane(void)                         /* a bad chain (blank / damaged settings): defaults */
{
    uint32_t i, ok = arrangement.count >= 1u && arrangement.count <= ARR_STEPS;
    for (i = 0; ok && i < arrangement.count; i++)
        ok = arrangement.entry[i].scene < ARR_SCENES && arrangement.entry[i].bars >= 1u && arrangement.entry[i].bars <= 64u;
    if (!ok)
        arr_defaults(&arrangement);
    if (song_cursor >= arrangement.count)
        song_cursor = (uint8_t)(arrangement.count - 1u);
}

/* SONG: the chain of sections (A..D in the track colours), bars of each, where the song is */
static void song_screen_draw(void)
{
    song_sane();
    uint32_t i, start = song_cursor > 3u ? song_cursor - 3u : 0u;
    static uint32_t previous;
    static const uint16_t SC[4] = {RGB(40, 124, 255), RGB(30, 204, 112), RGB(255, 198, 24), RGB(255, 98, 26)};
    uint32_t sig = song_cursor + 17u * arrangement_enabled + 37u * song.playing +
                   71u * arrangement_clock.index + 127u * arrangement_clock.bar +
                   257u * arrangement.count + 509u * song.g[G_BPM];
    char b[30];
    for (i = 0; i < arrangement.count; i++)
        sig = sig * 31u + arrangement.entry[i].scene + 7u * arrangement.entry[i].bars;
    for (i = 0; i < ARR_SCENES; i++) sig = sig * 3u + (uint32_t)project_used(i);
    if (!ui.force && !ui.msg_t && sig == previous) return;
    previous = ui.msg_t ? ~sig : sig;               /* redraw after a message expires */
    /* Draw one small band at a time: never exceed the 124-row canvas. */
    cv_begin(240, 40, C_BLACK);
    cv_text(4, 4, &FONT_S, ui_text(UI_SONG), C_WHITE);
    cv_text(60, 20, &FONT_S, ui_text(arrangement_enabled ? UI_SONG_MODE : UI_LOOP_MODE),
            arrangement_enabled ? SC[3] : RGB(118, 118, 126));
    fmt_int(b, song.g[G_BPM]);
    cv_text(236 - text_w(&FONT_S, b) - 28, 4, &FONT_S, b, C_WHITE);
    cv_text(236 - 24, 4, &FONT_S, "bpm", RGB(118, 118, 126));
    cv_text(236 - text_w(&FONT_S, ui_text(song.playing ? UI_PLAYING : UI_STOPPED)), 20, &FONT_S,
            ui_text(song.playing ? UI_PLAYING : UI_STOPPED), song.playing ? SC[1] : RGB(118, 118, 126));
    cv_rect(0, 39, 240, 1, RGB(26, 26, 30));
    cv_blit(0, 0);
    for (i = 0; i < 5u; i++) {
        uint32_t pos = start + i;
        cv_begin(240, 26, C_BLACK);
        if (pos < arrangement.count) {
            const arr_entry_t *e = &arrangement.entry[pos];
            int selected = pos == song_cursor, used = project_used(e->scene);
            uint16_t sc = SC[e->scene & 3u];
            int32_t w;
            fmt_int(b, (int32_t)pos + 1);
            cv_text(4, 5, &FONT_S, b, selected ? C_WHITE : RGB(118, 118, 126));
            cv_rect(30, 3, 22, 20, used ? sc : RGB(26, 26, 30));   /* the section tile */
            b[0] = (char)('A' + e->scene); b[1] = 0;
            cv_text(37, 5, &FONT_S, b, used ? C_BLACK : sc);
            w = e->bars * 120 / 64 + 4;                 /* its length as a bar */
            cv_rect(60, 9, w, 8, used ? (selected ? sc : RGB(54, 54, 60)) : RGB(26, 26, 30));
            fmt_int(b, e->bars);
            {   /* The bar at 64 bars leaves only 46 px for the number; omit its suffix if needed. */
                const char *suffix = ui_text(e->bars == 1 ? UI_BAR_SUFFIX : UI_BARS_SUFFIX);
                int32_t x = 60 + w + 6;
                if (text_w(&FONT_S, b) + text_w(&FONT_S, suffix) <= 236 - x)
                    str_cpy(b + str_len(b), suffix, sizeof b - str_len(b));
                cv_text(x, 5, &FONT_S, used ? b : ui_text(UI_EMPTY), selected ? C_WHITE : RGB(118, 118, 126));
            }
            if (arrangement_clock.running && arrangement_clock.index == pos) {
                cv_rect(60, 19, (int32_t)(arrangement_clock.bar + 1u) * w / (e->bars ? e->bars : 1), 2, C_WHITE);
                cv_rect(226, 9, 9, 9, SC[1]);
            }
            if (selected) cv_rect(0, 1, 240, 1, RGB(54, 54, 60)), cv_rect(0, 24, 240, 1, RGB(54, 54, 60));
        }
        cv_blit(0, 42 + 26u * i);
    }
    cv_begin(240, 68, C_BLACK);
    if (ui.msg_t) {
        cv_rect(0, 4, 240, 30, C_WHITE);
        cv_text((240 - text_w(&FONT_S, ui.msg)) / 2, 11, &FONT_S, ui.msg, C_BLACK);
    } else {
        static const ui_string_id_t L[4] = {UI_ENTRY_LAB, UI_SECTION_LAB, UI_BARS_LAB, UI_LENGTH_LAB};
        for (i = 0; i < 4u; i++) {
            cv_rect((int32_t)i * 60 + 4, 6, 52, 3, SC[i]);
            cv_text((int32_t)i * 60 + 30 - text_w(&FONT_S, ui_text(L[i])) / 2, 12,
                    &FONT_S, ui_text(L[i]), RGB(118, 118, 126));
        }
    }
    cv_text(4, 34, &FONT_S, ui_text(UI_SONG_HINT1), RGB(196, 196, 204));
    cv_text(4, 50, &FONT_S, ui_text(UI_SONG_HINT2), RGB(118, 118, 126));
    cv_blit(0, 172);
}

static void song_screen_input(uint32_t pressed, uint32_t home)
{
    uint32_t k, b;
    int32_t steps;
    song_sane();
    if (home == 1u) { go_home(); return; }       /* BT_TAP */
    for (k = 0; k < NB; k++) {
        if (!((pressed >> panel.btn[k]) & 1u)) continue;
        b = k;
        if ((b == B_PLAY || b == B_REC) && ft_owns_press())
            continue;                            /* (they close a free take: seq.c) */
        if (b == B_PLAY) {
            if (!song.playing && arrangement_enabled && !arr_valid(&arrangement, arrangement_ready())) {
                ui_message(ui_text(UI_EMPTY_SECTION));
            } else transport_req = song.playing ? 2 : 1;
        } else if (b == B_SEQ) {
            open_family(FAM_SEQ);
        } else if (b == B_SAVE || b == B_REC || b == B_OCTDN || b == B_OCTUP) {
            uint32_t scene = arrangement.entry[song_cursor].scene;
            if (song.playing || transport_req) { ui_message(ui_text(UI_STOP_FIRST)); continue; }
            if (b == B_SAVE) {
                arrangement_save();
                song_store_armed = 0;
            } else if (b == B_OCTDN) {
                arrangement_enabled ^= 1u;
                ui_message(ui_text(arrangement_enabled ? UI_SONG_MODE : UI_LOOP_MODE));
            } else if (b == B_OCTUP) {                   /* load: a second press within 3 s (unsaved work goes) */
                if (song_load_armed && (int32_t)(fm1_ms - song_store_deadline) <= 0) {
                    song_load_armed = 0;
                    project_load(scene);
                } else {
                    song_load_armed = 1;
                    song_store_armed = 0;
                    song_store_deadline = fm1_ms + 3000u;
                    ui_message(ui_text(UI_LOAD_AGAIN));
                }
            } else if (project_used(scene) &&
                       (!song_store_armed || (int32_t)(fm1_ms - song_store_deadline) > 0)) {
                song_store_armed = 1;
                song_store_deadline = fm1_ms + 3000u;
                ui_message(ui_text(UI_REPLACE_AGAIN));
            } else {
                project_save(scene);
                settings_save();
                song_store_armed = 0;
            }
        }
    }
    for (k = 0; k < 4u; k++) {
        steps = panel_enc(EN_K1 + k);
        if (!steps) continue;
        song_store_armed = 0;
        song_load_armed = 0;
        if (k == 0) {
            song_cursor = (uint8_t)clamp(song_cursor + steps, 0, arrangement.count - 1);
            continue;
        }
        if (song.playing || transport_req) { ui_message(ui_text(UI_STOP_FIRST)); continue; }
        if (k == 1) arrangement.entry[song_cursor].scene = (uint8_t)clamp(arrangement.entry[song_cursor].scene + steps, 0, 3);
        if (k == 2) arrangement.entry[song_cursor].bars = (uint8_t)clamp(arrangement.entry[song_cursor].bars + steps, 1, 64);
        if (k == 3) {
            arrangement.count = (uint8_t)clamp(arrangement.count + steps, 1, ARR_STEPS);
            if (song_cursor >= arrangement.count) song_cursor = arrangement.count - 1;
        }
    }
    /* Unused encoders have no hidden action on this screen. */
    panel_enc(EN_SELECT); panel_enc(EN_ALGO); panel_enc(EN_PRESET);
}
