# CONTEXT.md

## Glossary

- **مشهد (Scene)** — وحدة بصرية ضمن الحلقة. يُسمّى تلقائيًا "مشهد 1"، "مشهد 2"...
- **عملية توليد (Generation)** — طلب غير متزامن واحد إلى OpenRouter لإنشاء فيديو.
- **فيديو (Video)** — الملف الناتج MP4. يُحمّل محليًا ثم يُرفع إلى Google Drive.

## Domain Model

- `Episode` has many `Scene`s
- `Scene` has many `VideoGeneration`s
- `VideoGeneration` produces one video file

## Key Decisions

- Only assigned users and admins can create/delete scenes and trigger generations.
- Videos are downloaded locally first, then uploaded to Google Drive, then deleted locally.
- Video playback streams from Google Drive via iframe embed.
- OpenRouter model list is cached for 6 hours.
- Client-side polling every 10 seconds for generation status.
