# ocatom - Lokalna instalacja

Instrukcja instalacji i uruchomienia projektu ocatom na lokalnym środowisku Ubuntu.

Wymagania wstępne
Zainstalowany Python 3.12+
Zainstalowany PostgreSQL
Zainstalowany Git
Zainstalowany curl
Zainstalowany Poetry
Virtualenv (opcjonalnie, jeśli nie używasz Poetry do zarządzania środowiskami)
Krok 1: Instalacja wymaganych pakietów
Uruchom następujące polecenia, aby zainstalować niezbędne pakiety:

```
bash sudo apt update
sudo apt install python3 python3-venv python3-pip git curl postgresql postgresql-contrib 
```

Krok 2: Klonowanie repozytorium
Pobierz kod źródłowy projektu:

```
bash git clone https://github.com/araucaria-project/ocatom.git
cd ocatom 
```

Krok 3: Utworzenie i aktywacja wirtualnego środowiska

```
bash python3 -m venv venv
source venv/bin/activate 
```

Krok 4: Instalacja Poetry

```
bash curl -sSL https://install.python-poetry.org | python3 - 
```

Dodaj Poetry do zmiennej PATH:

```
bash export PATH="$HOME/.local/bin:$PATH" 
```

Sprawdzenie poprawności instalacji:

```
bash poetry -V 
```

Krok 5: Instalacja zależności
Uruchom:

```
bash poetry install 
```

Krok 6: Konfiguracja bazy danych PostgreSQL
Uruchom PostgreSQL:

```
bash sudo service postgresql start 
```

Wejdź do konsoli PostgreSQL:

```
bash sudo -u postgres psql 
```

W konsoli PostgreSQL wykonaj:

```
sql CREATE DATABASE ocatom;
GRANT ALL PRIVILEGES ON DATABASE ocatom TO postgres;
\q 
```

Jeśli użytkownik postgres nie ma hasła, ustaw je:

```
bash sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'postgres';
\q 
```

Krok 7: Zbieranie statycznych plików

```
bash python manage.py collectstatic 
```

Krok 8: Migracje bazy danych

```
bash python manage.py migrate 
```

Krok 9: Uruchomienie serwera lokalnego

```
<!-- bash python manage.py runserver  -->
poetry run python manage.py runserver
```

Serwer będzie dostępny pod adresem: http://127.0.0.1:8000

Problemy i debugowanie
Jeśli występują problemy z uprawnieniami do plików statycznych, sprawdź:

```
bash sudo chown -R www-data:www-data /home/ubuntu/tom_base/staticfiles/
sudo chmod -R 755 /home/ubuntu/tom_base/staticfiles/ 
```

Zakończenie
Jeśli wszystko poszło zgodnie z planem, aplikacja powinna działać lokalnie! 🚀 ```

