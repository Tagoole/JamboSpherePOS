## Jambo Sphere POS (Django)

Simple Point of Sale prototype built with Django.

### Features

- Add products
- Record sales
- View daily totals
- Sign up and login pages
- HTMX-based partial updates for smoother UI interactions

## Windows Setup (uv)

Use this path if you want the same tooling used in this project.

### 1. Install prerequisites

1. Install Python 3.12+.
2. Install uv from the official docs: https://docs.astral.sh/uv/getting-started/installation/
3. Open PowerShell in the project folder.

### 2. Create and activate virtual environment

```powershell
uv venv
.venv\Scripts\Activate.ps1
```

If script execution is blocked in PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
uv pip install -e .
```

### 4. Run migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 5. Create admin user (optional)

```powershell
python manage.py createsuperuser
```

### 6. Start development server

```powershell
python manage.py runserver
```

Open: http://127.0.0.1:8000/

### 7. Verify project health

```powershell
python manage.py check
```

## Windows Setup (pip)

Use this path if you prefer classic pip workflow.

### 1. Install prerequisites

1. Install Python 3.12+.
2. Open PowerShell in the project folder.

### 2. Create and activate virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install django>=6.0.4
```

Alternative (installs from project metadata):

```powershell
pip install -e .
```

### 4. Run migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 5. Create admin user (optional)

```powershell
python manage.py createsuperuser
```

### 6. Start development server

```powershell
python manage.py runserver
```

Open: http://127.0.0.1:8000/

### 7. Verify project health

```powershell
python manage.py check
```

## Typical Usage Flow

1. Sign up or log in.
2. Go to Products and add product name and price.
3. Go to Sales and record a sale.
4. Open Dashboard or Daily Totals to review total sales.

## Notes

- Default database is SQLite (`db.sqlite3`).
- If model changes are made, run migrations again.
- Use HTMX endpoints and templates already present in the project for partial page updates.
