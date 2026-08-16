# Robot error / alarm knowledge base (Jarvis)

Source: *Multiple servo driven robots — user manual with touch screen teach
pendant* (take-out robot for injection-molding machines), sections 37 (Error)
and 38 (Alarm).

The manual is split into **6 tables** — 3 error types + 3 alarm types:

| File | Type (VI) | Codes | Rows |
|------|-----------|-------|------|
| `operation_error.csv`    | Lỗi thao tác (Operation error)      | 01–250   | 97 |
| `setting_error.csv`      | Lỗi cài đặt (Setting error/change)  | 70–88,170–171 | 19 |
| `inappropriate_home.csv` | Lỗi vị trí home (Inappropriate home)| 90–198   | 31 |
| `system_alarm.csv`       | Cảnh báo hệ thống (System alarm)    | 01–47    | 29 |
| `axis_alarm.csv`         | Cảnh báo trục/servo (Axis alarm)    | 01–49    | 9  |
| `alarm.csv`              | Cảnh báo chung (Alarm)              | 01–199   | 84 |

`all_errors.csv` = the 6 tables combined (`type,code,content`) for the bot to load.

Columns: `code`, `content`. `content` merges the manual's *name / description /
cause / remedy* columns (the PDF's 3-column layout was flattened during
extraction). The bot re-splits this into **mô tả / nguyên nhân / khắc phục**
when answering. Rows can be hand-corrected freely; keep the header row.

## Bot behavior (Jarvis robot-error mode)

1. **Enter mode**: user says e.g. *"lỗi robot 10"* (error) or mentions
   *cảnh báo / alarm* + a number.
2. **Exit mode**: user says *"kết thúc robot"*.
3. **Answer format** (in the speaker's language): mô tả chi tiết lỗi →
   nguyên nhân → cách khắc phục.
4. **Not enough info**: if the code/type is missing or the request is
   incomplete to match a table row, the bot asks the user back for the missing
   detail (e.g. the code number), then answers.
5. **Type unclear (error vs alarm)**: if the same number exists in more than one
   table, the bot asks *"Bạn muốn hỏi CẢNH BÁO (alarm) hay LỖI (error)?"*.
   If still unclear, it **summarizes all matching types** for that same number.
6. **Always append** a reminder that alarm (cảnh báo) and error (lỗi) are
   different things and should be distinguished.
