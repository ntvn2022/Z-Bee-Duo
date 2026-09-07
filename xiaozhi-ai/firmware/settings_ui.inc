// [custom] On-device settings UI (included inside LcdDisplay::SetupUI).
// 3-tap bottom-right corner -> password 12345 -> multi-page settings.
//   Page 0: Screen off timer 0..600s (0 = never). NVS "ruanqinghe"/"scr_off_s".
//   Page 1: Volume 0..100%. Applied to the ES8311 codec + Settings "audio".
// Navigate with Back / Next. Uses only lv_obj + lv_label so it always compiles.
{
    // Defined in the board .cc. While the overlay is open the raw TouchTask must
    // not toggle listen/talk (taps go to these LVGL widgets instead).
    extern volatile bool g_settings_open;

    struct SUI {
        lv_obj_t* win;
        lv_obj_t* pass;
        lv_obj_t* cfg;
        lv_obj_t* pdisp;
        char buf[8];
        int blen;
        int page;          // 0 = screen-off, 1 = volume
        lv_obj_t* title;
        lv_obj_t* track;
        lv_obj_t* fill;
        lv_obj_t* val;
        int scr_value;     // screen-off seconds (0..600)
        int vol_value;     // volume percent (0..100)
        int track_w;
    };
    static SUI* g = new SUI();
    g->blen = 0;
    g->buf[0] = 0;
    g->page = 0;
    g->scr_value = 5;
    g->vol_value = 70;
    g->track_w = 200;

    // read current screen-off value from NVS
    {
        nvs_handle_t h;
        if (nvs_open("ruanqinghe", NVS_READONLY, &h) == ESP_OK) {
            int32_t x;
            if (nvs_get_i32(h, "scr_off_s", &x) == ESP_OK) g->scr_value = (int)x;
            nvs_close(h);
        }
    }
    // read current volume from Settings (safe during setup; codec may not be ready yet)
    {
        Settings s("audio", false);
        g->vol_value = s.GetInt("output_volume", 70);
        if (g->vol_value < 0) g->vol_value = 0;
        if (g->vol_value > 100) g->vol_value = 100;
    }

    // Give a button a clear pressed-state color so a tap is visibly registered.
    auto style_btn = [](lv_obj_t* b) {
        lv_obj_set_style_bg_opa(b, LV_OPA_COVER, 0);
        lv_obj_set_style_bg_color(b, lv_color_hex(0xF0F0F0), 0);
        lv_obj_set_style_border_color(b, lv_color_hex(0xBBBBBB), 0);
        lv_obj_set_style_border_width(b, 1, 0);
        lv_obj_set_style_radius(b, 4, 0);
        lv_obj_set_style_bg_color(b, lv_color_hex(0x1976D2), LV_STATE_PRESSED);
        lv_obj_set_style_bg_opa(b, LV_OPA_COVER, LV_STATE_PRESSED);
    };

    // full-screen overlay on the top layer (hidden by default)
    g->win = lv_obj_create(lv_layer_top());
    lv_obj_set_size(g->win, LV_HOR_RES, LV_VER_RES);
    lv_obj_set_style_bg_color(g->win, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(g->win, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_all(g->win, 4, 0);
    lv_obj_set_style_border_width(g->win, 0, 0);
    lv_obj_remove_flag(g->win, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(g->win, LV_OBJ_FLAG_HIDDEN);

    // ---------- password panel ----------
    g->pass = lv_obj_create(g->win);
    lv_obj_set_size(g->pass, lv_pct(100), lv_pct(100));
    lv_obj_set_style_pad_all(g->pass, 2, 0);
    lv_obj_set_style_border_width(g->pass, 0, 0);
    lv_obj_remove_flag(g->pass, LV_OBJ_FLAG_SCROLLABLE);

    // Exit button so you are never trapped on the password screen.
    lv_obj_t* pexit = lv_obj_create(g->pass);
    lv_obj_set_size(pexit, 34, 26);
    lv_obj_align(pexit, LV_ALIGN_TOP_LEFT, 2, 2);
    lv_obj_set_style_pad_all(pexit, 0, 0);
    style_btn(pexit);
    lv_obj_add_flag(pexit, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* pxl = lv_label_create(pexit); lv_label_set_text(pxl, "X"); lv_obj_center(pxl);
    lv_obj_add_event_cb(pexit, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        lv_obj_add_flag(u->win, LV_OBJ_FLAG_HIDDEN);
        g_settings_open = false;
    }, LV_EVENT_CLICKED, g);

    lv_obj_t* pt = lv_label_create(g->pass);
    lv_label_set_text(pt, "Password:");
    lv_obj_align(pt, LV_ALIGN_TOP_LEFT, 44, 6);
    g->pdisp = lv_label_create(g->pass);
    lv_label_set_text(g->pdisp, "");
    lv_obj_align(g->pdisp, LV_ALIGN_TOP_RIGHT, -8, 4);

    static const char* keys[12] = {"1","2","3","4","5","6","7","8","9","C","0","OK"};
    for (int i = 0; i < 12; i++) {
        lv_obj_t* b = lv_obj_create(g->pass);
        lv_obj_set_size(b, 66, 40);
        int col = i % 3, row = i / 3;
        lv_obj_align(b, LV_ALIGN_TOP_LEFT, 10 + col * 74, 34 + row * 46);
        lv_obj_set_style_pad_all(b, 0, 0);
        style_btn(b);
        lv_obj_add_flag(b, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_set_user_data(b, (void*)keys[i]);
        lv_obj_t* bl = lv_label_create(b);
        lv_label_set_text(bl, keys[i]);
        lv_obj_center(bl);
        lv_obj_add_event_cb(b, [](lv_event_t* e) {
            SUI* u = (SUI*)lv_event_get_user_data(e);
            lv_obj_t* t = (lv_obj_t*)lv_event_get_target(e);
            const char* k = (const char*)lv_obj_get_user_data(t);
            if (strcmp(k, "C") == 0) {
                u->blen = 0; u->buf[0] = 0;
            } else if (strcmp(k, "OK") == 0) {
                if (strcmp(u->buf, "12345") == 0) {
                    lv_obj_add_flag(u->pass, LV_OBJ_FLAG_HIDDEN);
                    lv_obj_remove_flag(u->cfg, LV_OBJ_FLAG_HIDDEN);
                } else {
                    u->blen = 0; u->buf[0] = 0;
                }
            } else if (u->blen < 6) {
                u->buf[u->blen++] = k[0];
                u->buf[u->blen] = 0;
            }
            char d[8]; int j;
            for (j = 0; j < u->blen; j++) d[j] = '*';
            d[j] = 0;
            lv_label_set_text(u->pdisp, d);
        }, LV_EVENT_CLICKED, g);
    }

    // ---------- config panel (multi-page) ----------
    g->cfg = lv_obj_create(g->win);
    lv_obj_set_size(g->cfg, lv_pct(100), lv_pct(100));
    lv_obj_set_style_pad_all(g->cfg, 2, 0);
    lv_obj_set_style_border_width(g->cfg, 0, 0);
    lv_obj_remove_flag(g->cfg, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(g->cfg, LV_OBJ_FLAG_HIDDEN);

    g->title = lv_label_create(g->cfg);
    lv_obj_align(g->title, LV_ALIGN_TOP_MID, 0, 6);
    g->val = lv_label_create(g->cfg);
    lv_obj_align(g->val, LV_ALIGN_TOP_MID, 0, 30);

    g->track = lv_obj_create(g->cfg);
    lv_obj_set_size(g->track, g->track_w, 26);
    lv_obj_align(g->track, LV_ALIGN_CENTER, 0, -8);
    lv_obj_set_style_pad_all(g->track, 0, 0);
    lv_obj_set_style_radius(g->track, 4, 0);
    lv_obj_set_style_bg_color(g->track, lv_color_hex(0xDDDDDD), 0);
    lv_obj_add_flag(g->track, LV_OBJ_FLAG_CLICKABLE);
    g->fill = lv_obj_create(g->track);
    lv_obj_set_style_pad_all(g->fill, 0, 0);
    lv_obj_set_style_border_width(g->fill, 0, 0);
    lv_obj_set_style_radius(g->fill, 4, 0);
    lv_obj_set_style_bg_color(g->fill, lv_color_hex(0x2196F3), 0);
    lv_obj_align(g->fill, LV_ALIGN_LEFT_MID, 0, 0);
    lv_obj_remove_flag(g->fill, LV_OBJ_FLAG_CLICKABLE);

    // Refresh the bar + label from the current page's value.  (Repeated inline in
    // handlers because LVGL event callbacks cannot capture.)
    auto refresh = [](SUI* u) {
        int mx = u->page ? 100 : 600;
        int v = u->page ? u->vol_value : u->scr_value;
        lv_obj_set_size(u->fill, u->track_w * v / mx, 26);
        if (u->page) lv_label_set_text_fmt(u->val, "%d %%", v);
        else if (v == 0) lv_label_set_text(u->val, "Never off");
        else lv_label_set_text_fmt(u->val, "%d sec", v);
        lv_label_set_text(u->title, u->page ? "Volume" : "Screen off (sec)");
    };
    refresh(g);

    // tap / drag on the track to set the value
    lv_obj_add_event_cb(g->track, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        lv_indev_t* indev = lv_indev_active();
        if (!indev) return;
        lv_point_t p; lv_indev_get_point(indev, &p);
        lv_area_t a; lv_obj_get_coords(u->track, &a);
        int w = a.x2 - a.x1; if (w < 1) w = 1;
        int rel = p.x - a.x1; if (rel < 0) rel = 0; if (rel > w) rel = w;
        int mx = u->page ? 100 : 600;
        int v = rel * mx / w;
        if (u->page) {
            u->vol_value = v;
            auto c = Board::GetInstance().GetAudioCodec();
            if (c) c->SetOutputVolume(v);
        } else {
            u->scr_value = v;
        }
        lv_obj_set_size(u->fill, u->track_w * v / mx, 26);
        if (u->page) lv_label_set_text_fmt(u->val, "%d %%", v);
        else if (v == 0) lv_label_set_text(u->val, "Never off");
        else lv_label_set_text_fmt(u->val, "%d sec", v);
    }, LV_EVENT_PRESSING, g);

    // - / + buttons (step 10s for screen, 5% for volume)
    lv_obj_t* minus = lv_obj_create(g->cfg);
    lv_obj_set_size(minus, 48, 38);
    lv_obj_align(minus, LV_ALIGN_CENTER, -140, -8);
    style_btn(minus);
    lv_obj_add_flag(minus, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* ml = lv_label_create(minus); lv_label_set_text(ml, "-"); lv_obj_center(ml);
    lv_obj_add_event_cb(minus, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        if (u->page) {
            u->vol_value -= 5; if (u->vol_value < 0) u->vol_value = 0;
            auto c = Board::GetInstance().GetAudioCodec();
            if (c) c->SetOutputVolume(u->vol_value);
        } else {
            u->scr_value -= 10; if (u->scr_value < 0) u->scr_value = 0;
        }
        int mx = u->page ? 100 : 600;
        int v = u->page ? u->vol_value : u->scr_value;
        lv_obj_set_size(u->fill, u->track_w * v / mx, 26);
        if (u->page) lv_label_set_text_fmt(u->val, "%d %%", v);
        else if (v == 0) lv_label_set_text(u->val, "Never off");
        else lv_label_set_text_fmt(u->val, "%d sec", v);
    }, LV_EVENT_CLICKED, g);

    lv_obj_t* plus = lv_obj_create(g->cfg);
    lv_obj_set_size(plus, 48, 38);
    lv_obj_align(plus, LV_ALIGN_CENTER, 140, -8);
    style_btn(plus);
    lv_obj_add_flag(plus, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* pl = lv_label_create(plus); lv_label_set_text(pl, "+"); lv_obj_center(pl);
    lv_obj_add_event_cb(plus, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        if (u->page) {
            u->vol_value += 5; if (u->vol_value > 100) u->vol_value = 100;
            auto c = Board::GetInstance().GetAudioCodec();
            if (c) c->SetOutputVolume(u->vol_value);
        } else {
            u->scr_value += 10; if (u->scr_value > 600) u->scr_value = 600;
        }
        int mx = u->page ? 100 : 600;
        int v = u->page ? u->vol_value : u->scr_value;
        lv_obj_set_size(u->fill, u->track_w * v / mx, 26);
        if (u->page) lv_label_set_text_fmt(u->val, "%d %%", v);
        else if (v == 0) lv_label_set_text(u->val, "Never off");
        else lv_label_set_text_fmt(u->val, "%d sec", v);
    }, LV_EVENT_CLICKED, g);

    // Back / Next to flip pages
    lv_obj_t* back = lv_obj_create(g->cfg);
    lv_obj_set_size(back, 88, 34);
    lv_obj_align(back, LV_ALIGN_BOTTOM_LEFT, 12, -46);
    style_btn(back);
    lv_obj_add_flag(back, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* bkl = lv_label_create(back); lv_label_set_text(bkl, "< Back"); lv_obj_center(bkl);
    lv_obj_add_event_cb(back, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        u->page = u->page ? 0 : 1;
        int mx = u->page ? 100 : 600;
        int v = u->page ? u->vol_value : u->scr_value;
        lv_obj_set_size(u->fill, u->track_w * v / mx, 26);
        if (u->page) lv_label_set_text_fmt(u->val, "%d %%", v);
        else if (v == 0) lv_label_set_text(u->val, "Never off");
        else lv_label_set_text_fmt(u->val, "%d sec", v);
        lv_label_set_text(u->title, u->page ? "Volume" : "Screen off (sec)");
    }, LV_EVENT_CLICKED, g);

    lv_obj_t* next = lv_obj_create(g->cfg);
    lv_obj_set_size(next, 88, 34);
    lv_obj_align(next, LV_ALIGN_BOTTOM_RIGHT, -12, -46);
    style_btn(next);
    lv_obj_add_flag(next, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* nxl = lv_label_create(next); lv_label_set_text(nxl, "Next >"); lv_obj_center(nxl);
    lv_obj_add_event_cb(next, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        u->page = u->page ? 0 : 1;
        int mx = u->page ? 100 : 600;
        int v = u->page ? u->vol_value : u->scr_value;
        lv_obj_set_size(u->fill, u->track_w * v / mx, 26);
        if (u->page) lv_label_set_text_fmt(u->val, "%d %%", v);
        else if (v == 0) lv_label_set_text(u->val, "Never off");
        else lv_label_set_text_fmt(u->val, "%d sec", v);
        lv_label_set_text(u->title, u->page ? "Volume" : "Screen off (sec)");
    }, LV_EVENT_CLICKED, g);

    // Save / Close
    lv_obj_t* save = lv_obj_create(g->cfg);
    lv_obj_set_size(save, 90, 38);
    lv_obj_align(save, LV_ALIGN_BOTTOM_LEFT, 12, -6);
    style_btn(save);
    lv_obj_add_flag(save, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* svl = lv_label_create(save); lv_label_set_text(svl, "Save"); lv_obj_center(svl);
    lv_obj_add_event_cb(save, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        nvs_handle_t h;
        if (nvs_open("ruanqinghe", NVS_READWRITE, &h) == ESP_OK) {
            nvs_set_i32(h, "scr_off_s", u->scr_value);
            nvs_commit(h);
            nvs_close(h);
        }
        {
            Settings s("audio", true);
            s.SetInt("output_volume", u->vol_value);
        }
        auto c = Board::GetInstance().GetAudioCodec();
        if (c) c->SetOutputVolume(u->vol_value);
        lv_obj_add_flag(u->win, LV_OBJ_FLAG_HIDDEN);
        g_settings_open = false;
    }, LV_EVENT_CLICKED, g);

    lv_obj_t* close = lv_obj_create(g->cfg);
    lv_obj_set_size(close, 90, 38);
    lv_obj_align(close, LV_ALIGN_BOTTOM_RIGHT, -12, -6);
    style_btn(close);
    lv_obj_add_flag(close, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* cll = lv_label_create(close); lv_label_set_text(cll, "Close"); lv_obj_center(cll);
    lv_obj_add_event_cb(close, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        lv_obj_add_flag(u->win, LV_OBJ_FLAG_HIDDEN);
        g_settings_open = false;
    }, LV_EVENT_CLICKED, g);

    // ---------- 3-tap bottom-right corner to open ----------
    lv_obj_t* corner = lv_obj_create(screen);
    lv_obj_set_size(corner, 56, 56);
    lv_obj_align(corner, LV_ALIGN_BOTTOM_RIGHT, 0, 0);
    lv_obj_set_style_bg_opa(corner, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(corner, 0, 0);
    lv_obj_add_flag(corner, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(corner, [](lv_event_t* e) {
        SUI* u = (SUI*)lv_event_get_user_data(e);
        static uint32_t last = 0;
        static int cnt = 0;
        uint32_t now = lv_tick_get();
        if (now - last < 1500) cnt++; else cnt = 1;
        last = now;
        if (cnt >= 3) {
            cnt = 0;
            u->blen = 0; u->buf[0] = 0;
            u->page = 0;
            lv_label_set_text(u->pdisp, "");
            lv_obj_remove_flag(u->pass, LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_flag(u->cfg, LV_OBJ_FLAG_HIDDEN);
            lv_obj_remove_flag(u->win, LV_OBJ_FLAG_HIDDEN);
            g_settings_open = true;
        }
    }, LV_EVENT_CLICKED, g);
}
