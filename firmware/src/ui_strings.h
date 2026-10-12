/* SPDX-License-Identifier: GPL-3.0-only */
#pragma once
#include <stdint.h>
/* Display resources only. Device protocol identifiers remain ASCII. */
typedef enum {
#define UI_STRING(id, en, ja) UI_##id,
#include "ui_strings.def"
#undef UI_STRING
    UI_STRING_COUNT
} ui_string_id_t;

#ifdef UI_ENABLE_LANGUAGE_SWITCH
static const char *const ui_strings_en[] = {
#define UI_STRING(id, en, ja) en,
#include "ui_strings.def"
#undef UI_STRING
};
#endif
#include "../../build/gen/felucca_ui_hash.h"

static const char *ui_text(ui_string_id_t id)
{
    return (uint32_t)id < UI_STRING_COUNT ? (const char *)UI_JA_BLOB + UI_JA_OFF[id] : "?";
}

/* Existing page and parameter descriptors double as protocol metadata. Resolve
 * their display names at the drawing boundary so wire formats stay unchanged.
 * The hashes save the unused full English table in the Phase 2 firmware. */
static uint32_t ui_name_hash(const char *s)
{
    uint32_t h = 2166136261u;
    while (*s) h = (h ^ (uint8_t)*s++) * 16777619u;
    return h;
}
static const char *ui_display_name(const char *en)
{
    uint32_t i, h;
    if (!en) return "";
    h = ui_name_hash(en);
    for (i = 0; i < UI_STRING_COUNT; i++) {
        if (h == UI_EN_HASH[i])
            return ui_text((ui_string_id_t)i);
    }
    return en;
}
