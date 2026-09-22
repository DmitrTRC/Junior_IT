# Бэкап students/ на NAS

Приватные данные учеников (`students/`, не в гите) раз в час зеркалятся на
QNAP: `/Volumes/BACKUP-VIDEO/JuniorIT/students/`. Шара не смонтирована — тик
пропускается, в лог одна строка.

## Установка

```bash
cp provisioning/students-backup/com.juniorit.students-backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.juniorit.students-backup.plist
```

Проверка руками: `bash tools/students_backup.sh` → `… ok N файлов → …`.
Лог: `~/Library/Logs/junior-it-students-backup.log`. Статус — карточка
`students-backup` во вкладке `processes`.
