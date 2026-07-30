# Restriction Generator 1.0

[English version](README.md)

Aplikacja okienkowa do tworzenia datapacków dla Jobs+ i Item Restrictions
w Minecraft 1.21.1. Skanuje pliki JAR modów NeoForge, odczytuje receptury,
wykrywa materiały i rodzaje przedmiotów, a następnie tworzy edytowalne
wymagania profesji i poziomów.

## Najważniejsze funkcje

- polski i angielski interfejs
- domyślna konfiguracja Vanilla oraz zapisywane profile
- niezależne profesje i poziomy dla używania, craftingu, enchantowania oraz
  naprawy
- odczyt receptur kształtowych, bezkształtowych, kowalskich, tagów i wielu
  niestandardowych pól wyniku
- reguły materiałów pozwalające ustawić setki przedmiotów jednocześnie
- ikony przedmiotów i składników odczytywane z lokalnych plików Minecrafta
  i modów
- własne ikony zastępcze, gdy lokalne zasoby są niedostępne
- wizualny podgląd receptury
- filtrowanie, sortowanie, zaznaczanie wielu pozycji i masowe usuwanie
- wyszukiwanie zatwierdzane Enterem na listach restrykcji i receptur
- dodawanie zaznaczonych przedmiotów jako neutralnych wpisów do ręcznej
  konfiguracji
- zaznaczanie wszystkich przedmiotów widocznych pod aktualnym filtrem
- wybór zgodnej wersji Minecrafta w zakładce Eksport
- eksport ZIP gotowy do folderu `datapacks` świata

Domyślna progresja Vanilla:

| Wyposażenie | Crafting | Używanie |
| --- | --- | --- |
| Diamentowe | Smith 20 | odpowiednia profesja 20 |
| Netheritowe | Smith 40 | odpowiednia profesja 40 |
| Maczuga i trójząb | bez zmian | Hunter 20 |

Kilofy używają profesji Miner, siekiery Lumberjack, motyki Farmer, a broń
i pancerz Hunter. Enchantowanie domyślnie używa Enchantera, a naprawa Smitha.
Każdy wygenerowany wpis można zmienić.

## Gotowa aplikacja Windows

Pobierz `RestrictionGenerator-1.0.0-Windows.exe` ze strony
[Releases](../../releases). Program jest przenośny i nie wymaga Pythona.

Windows może wyświetlić ostrzeżenie SmartScreen, ponieważ plik nie jest
podpisany płatnym certyfikatem. Przed uruchomieniem możesz sprawdzić sumę
kontrolną podaną w wydaniu.

## Uruchamianie ze źródeł

Wymagania:

- Python 3.13
- Windows 10 lub 11 (inne systemy mogą działać, ale nie były testowane)

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Budowanie pliku EXE

Uruchom `Zbuduj_aplikacje.bat` albo zainstaluj zależności kompilacji i użyj
dołączonego pliku PyInstaller:

```powershell
python -m pip install -r requirements-build.txt
pyinstaller --noconfirm RestrictionGenerator.spec
```

Gotowy plik pojawi się jako `dist/RestrictionGenerator.exe`.

## Lokalne zasoby i prywatność

Program odczytuje wyłącznie pliki wskazane lub znalezione na lokalnym
komputerze. Nie pobiera ani nie wysyła zasobów Minecrafta i modów.
Repozytorium oraz wydanie nie zawierają skopiowanych tekstur Mojang ani
innych modów. Szczegóły znajdują się w [ASSETS.md](ASSETS.md).

## Powiązane projekty

- [Jobs+ Armor Restrictions](https://github.com/Pyra00PL/jobs-armor-restrictions)
- [Jobs+ Requirement Tooltips](https://github.com/Pyra00PL/jobs-requirement-tooltips)

## Licencja

Kod aplikacji i oryginalne ikony zastępcze są udostępnione na licencji MIT.
Nazwy i znaki towarowe innych projektów należą do ich właścicieli.

TO NIE JEST OFICJALNY PRODUKT MINECRAFT. PROJEKT NIE JEST ZATWIERDZONY ANI
POWIĄZANY Z MOJANG LUB MICROSOFT.
