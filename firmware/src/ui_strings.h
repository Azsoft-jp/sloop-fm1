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

static const char *const ui_strings_en[] = {
#define UI_STRING(id, en, ja) en,
#include "ui_strings.def"
#undef UI_STRING
};
static const char *const ui_strings_ja[] = {
#define UI_STRING(id, en, ja) ja,
#include "ui_strings.def"
#undef UI_STRING
};

static const char *ui_text(ui_string_id_t id)
{
    return (uint32_t)id < UI_STRING_COUNT ? ui_strings_ja[id] : "?";
}

/* Existing page and parameter descriptors double as protocol metadata. Resolve
 * their display names at the drawing boundary so wire formats stay unchanged. */
static const char *ui_display_name(const char *en)
{
    uint32_t i;
    if (!en) return "";
    for (i = 0; i < UI_STRING_COUNT; i++) {
        const char *a = en, *b = ui_strings_en[i];
        while (*a && *a == *b) { a++; b++; }
        if (!*a && !*b)
            return ui_text((ui_string_id_t)i);
    }
    return en;
}
