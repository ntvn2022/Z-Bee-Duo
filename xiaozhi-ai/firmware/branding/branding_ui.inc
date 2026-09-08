// [custom] Topstar branding on the main screen: the Topstar logo on the
// left-middle and the robot product photo on the right-middle. Both are small
// (110px wide) and vertically centered, so they flank the central emoji and do
// not overlap the top status bar or the answer/question text rows.
// The image descriptors are defined at file scope via the *_img.inc includes.
{
    extern const lv_image_dsc_t img_topstar_logo;
    extern const lv_image_dsc_t img_robot;

    lv_obj_t* brand_logo = lv_image_create(screen);
    lv_image_set_src(brand_logo, &img_topstar_logo);
    lv_obj_align(brand_logo, LV_ALIGN_LEFT_MID, 2, 0);

    lv_obj_t* brand_robot = lv_image_create(screen);
    lv_image_set_src(brand_robot, &img_robot);
    lv_obj_align(brand_robot, LV_ALIGN_RIGHT_MID, -2, 0);
}
