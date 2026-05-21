# Manuel smoketest mod fysisk robot

Denne checkliste køres mod en rigtig Pepper/NAO. Den verificerer end-to-end at bridge'en starter, kan tale med NAOqi, og at hver registrerede kommando giver det forventede resultat på robotten.

Køres når:
- Den automatiserede test-suite (`pytest`) er grøn
- Du er på samme netværk som robotten
- Du sidder i nærheden af robotten og kan høre/se den reagere

Tag estimat: 10–15 min hvis intet fejler.

## 0. Forudsætninger

- [ ] Python 2.7-venv'en er sat op: `norma-robot-bridge/.venv27/`
- [ ] NAOqi SDK er importerbar fra venv'en — verificér med:
  ```bash
  ./.venv27/Scripts/python.exe -c "from naoqi import ALProxy; print('OK')"
  ```
  Hvis det fejler: tilføj NAOqi-SDK'ets `pynaoqi-2.x.x.x`-mappe til `PYTHONPATH` (sti afhænger af din SDK-installation).
- [ ] Robotten er tændt og du har dens IP (tryk på maveknappen — Pepper siger den højt)
- [ ] Du kan ping'e robotten: `ping <robot-ip>` får svar
- [ ] Port 9559 er åben mod robotten: `Test-NetConnection <robot-ip> -Port 9559` (Windows) eller `nc -z <robot-ip> 9559` (bash)

## 1. Konfigurer bridge

Lav en lokal config-fil ud fra reference-skabelonen:

```bash
cp config/default.ini config/local.ini
# Redigér config/local.ini og sæt [robot] ip = <din-robots-ip>
```

`config/local.ini` er gitignored — dine lokale ændringer bliver ikke commit'et. Bridge'en auto-loader `config/local.ini` hvis den findes, så `--config` er ikke længere påkrævet.

Alternativt: spring config-filen over og giv IP'en på kommandolinjen med `--robot-ip <din-robots-ip>`.

## 2. Start bridge

I én terminal:

```bash
cd norma-robot-bridge

# Anbefalet — auto-loader config/local.ini
PYTHONPATH=src ./.venv27/Scripts/python.exe -m norma_bridge.main

# Eller med eksplicit IP (overstyrer config og ENV)
PYTHONPATH=src ./.venv27/Scripts/python.exe -m norma_bridge.main --robot-ip <din-robots-ip>
```

Forventet:
- [ ] Logmeddelelse: `Auto-loadede config-fil: .../config/local.ini` (hvis ingen --config)
- [ ] Logmeddelelse: `Norma bridge starter: BridgeConfig(robot=<ip>:9559, ...)`
- [ ] Logmeddelelse: `Forbinder til NAOqi paa <ip>:9559`
- [ ] Hvis `[intro]` er udfyldt i config: robotten kører animation, viser tablet, siger velkomst
- [ ] Logmeddelelse: `Norma bridge lytter paa 0.0.0.0:8080`

Hvis det hænger ved "Forbinder til NAOqi": NAOqi-proxy'en kan ikke nå robotten. Stop med Ctrl+C og dobbelttjek IP/netværk.

## 3. Smoketest hver kommando

I en anden terminal, sæt en variabel og kør curl-kald nedenfor:

```bash
BRIDGE=http://localhost:8080   # eller http://<bridge-host>:8080 hvis bridge kører på en anden maskine
```

### 3.1 Status

```bash
curl $BRIDGE/api/status
```

Forventet respons:
```json
{"status":"success","data":{"ip":"<robot-ip>","port":9559,"interaction_count":0}}
```

- [ ] HTTP 200
- [ ] `interaction_count` er 0 (eller hvad intro-flowet efterlod)

### 3.2 say (TTS uden gesture)

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"say","params":{"text":"Hej, jeg er klar"}}'
```

- [ ] HTTP 200
- [ ] Response: `{"status":"success","data":{"spoken_text":"Hej, jeg er klar","gesture":null,"interaction_count":1}}`
- [ ] **Robotten siger sætningen højt**
- [ ] Cycling-logik: `interaction_count: 1` er ulige → ingen gesture (gesture=null) ✓

### 3.3 say (anden gang — med automatisk gesture)

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"say","params":{"text":"Og nu med en bevægelse"}}'
```

- [ ] HTTP 200
- [ ] `gesture` i respons er ikke-null (cycler til `calm` ved interaction 2)
- [ ] **Robotten siger sætningen OG laver en gesture**

### 3.4 say med eksplicit gesture

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"say","params":{"text":"Hej hej","gesture":"hello"}}'
```

- [ ] HTTP 200
- [ ] `gesture`: `"hello"` i respons
- [ ] **Robotten vinker mens den siger sætningen**

### 3.5 play_gesture (uden tale)

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"play_gesture","params":{"gesture_name":"bow"}}'
```

- [ ] HTTP 200
- [ ] Response: `{"status":"success","data":{"played":"bow"}}`
- [ ] **Robotten bukker uden at sige noget**
- [ ] Status (`curl $BRIDGE/api/status`) viser uændret `interaction_count` (play_gesture tæller ikke som interaktion)

### 3.6 show_tablet_url (foretrukken metode)

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_url","params":{"url":"https://example.com/"}}'
```

- [ ] HTTP 200
- [ ] Response: `{"status":"success","data":{"shown_url":"https://example.com/"}}`
- [ ] **Robotten viser example.com på sin tablet**

### 3.7 show_tablet_image (legacy data-URI)

Kræver et lokalt billede på *bridge-maskinen*:

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_image","params":{"image_path":"C:\\sti\\til\\test.png"}}'
```

- [ ] HTTP 200
- [ ] Response indeholder `shown_image` med absolut sti
- [ ] **Robotten viser billedet centreret på tabletten**

Med ikke-eksisterende fil:
```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_image","params":{"image_path":"/findes/ikke.png"}}'
```
- [ ] HTTP 400 (klient-fejl, ikke 500)
- [ ] Response: `{"status":"error","message":"Billedfil ikke fundet: ..."}`

### 3.8 show_tablet_html (legacy data-URI)

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_html","params":{"html":"<h1 style=\"font-size:8em;text-align:center\">Hej Norma</h1>"}}'
```

- [ ] HTTP 200
- [ ] Response: `{"status":"success","data":{"html_length":<n>}}`
- [ ] **Robotten viser overskriften "Hej Norma" på tabletten**

### 3.9 hide_tablet

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"hide_tablet","params":{}}'
```

- [ ] HTTP 200
- [ ] Response: `{"status":"success","data":{"hidden":true}}`
- [ ] **Tabletten bliver tom/sort**

### 3.10 Fejl-cases

```bash
# Ukendt kommando
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"banan","params":{}}'
```
- [ ] HTTP 400 (ikke 500)
- [ ] Response: `{"status":"error","message":"Ukendt kommando: banan"}`

```bash
# Manglende parameter
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"say","params":{}}'
```
- [ ] HTTP 400
- [ ] Response: `{"status":"error","message":"params.text mangler"}`

```bash
# Ugyldig JSON
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d 'ikke-gyldig-json'
```
- [ ] HTTP 400
- [ ] Response indeholder `"Ugyldig JSON"`

```bash
# Ukendt path
curl $BRIDGE/api/banan
```
- [ ] HTTP 404
- [ ] Response: `{"status":"error","message":"Not Found"}`

## 4. Æøå round-trip

```bash
curl -X POST $BRIDGE/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"say","params":{"text":"Pølsemand på rådhuspladsen"}}'
```

- [ ] HTTP 200
- [ ] `spoken_text` i respons indeholder æøå korrekt
- [ ] **Robotten udtaler ordene korrekt på dansk** (ikke "polsemand pa radhuspladsen")

## 5. Samtidighed

I én terminal, kør 5 kald i parallel:

```bash
for i in 1 2 3 4 5; do
    curl -X POST $BRIDGE/api/command \
         -H "Content-Type: application/json" \
         -d "{\"command\":\"say\",\"params\":{\"text\":\"Kald nummer $i\"}}" &
done
wait
```

- [ ] Alle 5 returnerer HTTP 200
- [ ] Hvert respons har et unikt `interaction_count` (1–5 i en eller anden rækkefølge)
- [ ] Robotten siger alle 5 sætninger sekventielt (NAOqi serialiserer TTS internt)
- [ ] Bridge'en logger alle 5 requests

## 6. Stop bridge

I terminalen hvor bridge kører:

- [ ] Tryk Ctrl+C
- [ ] Logmeddelelse: `Stopper bridge (Ctrl+C)`
- [ ] Process'en lukker rent (returnerer til prompt indenfor et par sekunder)

## 7. Genstart-tjek

- [ ] Start bridge igen med samme kommando
- [ ] `interaction_count` er nulstillet til 0 (state er ikke persistent — det er bevidst)
- [ ] Alle kommandoer fra trin 3 virker stadig

## Hvis noget fejler

| Symptom | Sandsynlig årsag | Fix |
|---|---|---|
| `from naoqi import ALProxy` fejler | NAOqi SDK ikke i `PYTHONPATH` | Tilføj `pynaoqi-2.x.x.x`-mappen til `PYTHONPATH` før kommandoen |
| Bridge hænger ved "Forbinder til NAOqi" | Robot uopnåelig | Tjek IP, ping, port 9559 |
| `say` returnerer 200 men robotten taler ikke | TTS-volumen muted, eller NAOqi ALTextToSpeech har problemer | Tjek robotens lydstyrke; tryk på maveknap og bed den sige sit navn manuelt |
| `play_gesture` 200 men ingen bevægelse | Tag-navn ikke genkendt af `ALAnimationPlayer.runTag` | Brug et legacy-navn fra `gestures.py` (`hello`, `happy`, `bow` osv.); tjek bridge-logs for warning |
| Tablet viser intet | Robotten har ikke en tablet, eller `ALTabletService` er ikke tilgængelig på dit NAOqi-build | Tjek på selve robotten via Choregraphe |
| 500 i stedet for 400 ved bad params | Bug i bridge | Rapporter — det skal være 400 jf. kontrakten |

## Når alt er grønt

- [ ] Alle ovenstående checks bestået
- [ ] Notér i commit-message at smoketesten er kørt mod robot `<navn/IP>` på dato `<dato>`
- [ ] Bridge er klar til at blive deployed på robot-værtsmaskinen
