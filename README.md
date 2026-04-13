# CRM API — Endpoints ro'yxati

## Auth  `/api/auth`
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| POST | `/login` | — | Login (token olish) |

---

## Admin  `/api/admin`  (faqat ADMIN)
| Method | URL | Description |
|--------|-----|-------------|
| GET    | `/users`          | Barcha foydalanuvchilar |
| POST   | `/users`          | Yangi foydalanuvchi yaratish |
| GET    | `/users/<id>`     | Bitta foydalanuvchi |
| PATCH  | `/users/<id>`     | Foydalanuvchini tahrirlash |
| DELETE | `/users/<id>`     | Foydalanuvchini o'chirish |

---

## Kurslar  `/api/courses`
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `` | ALL | Barcha kurslar |
| POST   | `` | ADMIN | Yangi kurs |
| GET    | `/<id>` | ALL | Bitta kurs |
| PATCH  | `/<id>` | ADMIN | Kursni tahrirlash |
| DELETE | `/<id>` | ADMIN | Kursni o'chirish |

---

## Guruhlar  `/api/groups`
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `` | ALL | Barcha guruhlar |
| POST   | `` | ADMIN | Yangi guruh (**darslar avtomatik yaratiladi**) |
| GET    | `/<id>` | ALL | Bitta guruh |
| PATCH  | `/<id>` | ADMIN | Guruhni tahrirlash |
| DELETE | `/<id>` | ADMIN | Guruh + darslarni o'chirish |
| POST   | `/<id>/generate-lessons` | ADMIN | Darslarni qayta generate qilish |

### Dars kunlari logikasi
- `schedule_type: "odd"`  → **Dushanba, Chorshanba, Juma** (weekday 0, 2, 4)
- `schedule_type: "even"` → **Seshanba, Payshanba, Shanba** (weekday 1, 3, 5)
- **Yakshanba hech qachon hisoblanmaydi**
- Guruh yaratilganda `start_date`–`end_date` oralig'idagi barcha to'g'ri kunlar uchun
  `Lesson` yozuvlari avtomatik qo'shiladi.

---

## Operator  `/api/operator`

### Leadlar
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/leads`        | ADMIN, OPERATOR | Leadlar ro'yxati |
| POST   | `/leads`        | ADMIN, OPERATOR | Yangi lead |
| GET    | `/leads/<id>`   | ADMIN, OPERATOR | Bitta lead |
| PATCH  | `/leads/<id>`   | ADMIN, OPERATOR | Leadni tahrirlash |
| DELETE | `/leads/<id>`   | ADMIN, OPERATOR | Leadni o'chirish |

**Lead statuslari:** `new`, `contacted`, `interested`, `rejected`, `converted`

### O'quvchilar
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/students`       | ALL | O'quvchilar ro'yxati |
| POST   | `/students`       | ADMIN, OPERATOR | Yangi o'quvchi |
| GET    | `/students/<id>`  | ALL | Bitta o'quvchi |
| PATCH  | `/students/<id>`  | ADMIN, OPERATOR | O'quvchini tahrirlash |
| DELETE | `/students/<id>`  | ADMIN | O'quvchini o'chirish |

### Enrollment (guruhga qo'shish)
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/enrollments`         | ALL | Ro'yxat |
| POST   | `/enrollments`         | ADMIN, OPERATOR | Guruhga qo'shish |
| PATCH  | `/enrollments/<id>`    | ALL | Status o'zgartirish |
| DELETE | `/enrollments/<id>`    | ADMIN | O'chirish |

**Enrollment statuslari:** `active`, `finished`, `dropped`

### To'lovlar
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/payments`        | ALL | To'lovlar ro'yxati |
| POST   | `/payments`        | ALL | To'lov qabul qilish |
| GET    | `/payments/<id>`   | ALL | Bitta to'lov |
| DELETE | `/payments/<id>`   | ADMIN, MANAGER | To'lovni o'chirish |

**To'lov turlari:** `cash`, `click`, `payme`

---

## Manager  `/api/manager`

### Davomat
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/attendance`         | ADMIN, MANAGER | Davomat ro'yxati (`?lesson_id=X` yoki `?student_id=Y`) |
| POST   | `/attendance`         | ADMIN, MANAGER | Davomat belgilash (batch) |
| PATCH  | `/attendance/<id>`    | ADMIN, MANAGER | Davomatni tahrirlash |
| DELETE | `/attendance/<id>`    | ADMIN, MANAGER | Davomatni o'chirish |

**Davomat statuslari:** `keldi`, `kelmadi`, `kechikdi`

**Davomat POST body example:**
```json
{
  "lesson_id": 5,
  "records": [
    {"student_id": 1, "status": "keldi"},
    {"student_id": 2, "status": "kelmadi"}
  ]
}
```

### Darslar
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/lessons`        | ADMIN, MANAGER | Darslar ro'yxati (`?group_id=X`) |
| GET    | `/lessons/<id>`   | ADMIN, MANAGER | Bitta dars |

### To'lovlar (manager ko'rinishi)
| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/payments/student/<id>` | ADMIN, MANAGER | O'quvchi to'lovlari |
| GET    | `/payments/summary`      | ADMIN, MANAGER | Oylik statistika |

---

## O'qituvchilar  `/api/teachers`  (ADMIN, MANAGER)

| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `` | ADMIN, MANAGER | Barcha o'qituvchilar |
| POST   | `` | ADMIN | Yangi o'qituvchi qo'shish |
| GET    | `/<id>` | ADMIN, MANAGER | Bitta o'qituvchi |
| PATCH  | `/<id>` | ADMIN | O'qituvchini tahrirlash |
| DELETE | `/<id>` | ADMIN | O'qituvchini o'chirish |
| POST   | `/salary-calculate` | ADMIN, MANAGER | Guruh uchun oylikni hisoblash va saqlash |
| GET    | `/<id>/salary-report` | ADMIN, MANAGER | O'qituvchining barcha oylik hisobotlari |

### O'qituvchi yaratish:
```json
{
  "full_name":      "Alisher Karimov",
  "phone_number":   "+998901234567",
  "salary_percent": 20
}
```

## Guruh oylik  `/api/groups`  (yangi endpointlar)

| Method | URL | Roles | Description |
|--------|-----|-------|-------------|
| GET    | `/<id>/salary-report` | ADMIN, MANAGER | Guruhning saqlangan oylik hisobotlari |
| GET    | `/<id>/salary-live?for_month=2025-04` | ADMIN, MANAGER | Jonli hisoblash (saqlamasdan) |

### Jonli hisobot javobi:
```json
{
  "total_payments":  5000000,
  "teacher_salary":  1000000,
  "net_profit":      4000000,
  "salary_percent":  20.0,
  "student_count":   12,
  "paid_students":   8
}
```

### Guruh yaratishda endi teacher_id tanlash mumkin:
```json
{
  "name":          "Python-1",
  "course_id":     1,
  "teacher_id":    3,
  "schedule_type": "odd",
  "lesson_time":   "10:00:00"
}
```

## Migratsiya (yangi jadvallar uchun)

Agar Alembic ishlatayotgan bo'lsangiz:
```bash
flask db migrate -m "add teacher and teacher_salary tables"
flask db upgrade
```

Agar db.create_all() ishlatayotgan bo'lsangiz (default):
Ilova birinchi marta ishga tushganda yangi jadvallar avtomatik yaratiladi.
