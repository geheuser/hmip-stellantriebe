# HmIP Stellantriebe

Home-Assistant-Integration, die den **Schaltausgang von Homematic-IP-Wandthermostaten**
(z. B. **HmIP-BWTH**) als Entität bereitstellt – also ob der angeschlossene
Stellantrieb der Fußbodenheizung gerade angesteuert wird.

## Warum?

Bei Homematic IP mit **Access Point (HmIP-HAP)** läuft alles über die Integration
[HomematicIP Cloud](https://www.home-assistant.io/integrations/homematicip_cloud/).
Die Cloud liefert den Zustand des internen Schaltausgangs mit
(Kanal `INTERNAL_SWITCH_CHANNEL`, Feld `valvePosition`), Home Assistant legt dafür
aber keine Entität an, und `hvac_action` gibt es nur für Heizkörperthermostate.

Diese Integration hängt sich an die **bestehende** HomematicIP-Cloud-Verbindung an:
keine zweite Cloud-Verbindung, keine Zugangsdaten, keine Abfragen – Änderungen kommen
in Echtzeit über den Websocket der Original-Integration.

## Entitäten (je Wandthermostat mit Schaltausgang)

| Entität | Beschreibung |
|---|---|
| `binary_sensor.<gerät>_stellantrieb` | **An** = Schaltausgang aktiv (Stellantrieb wird angesteuert). Attribut `climate_control_type`: `TWO_POINT_CONTROL` oder `PWM_CONTROL`. |
| `sensor.<gerät>_ventilstellung` | Ventilstellung in % – nur bei PWM-Regelung standardmäßig aktiv (bei Zweipunktregelung nur 0/100). |

Die Entitäten erscheinen direkt am vorhandenen Gerät der HomematicIP-Cloud-Integration.

**Heizstatus am Thermostat (ab 0.2.0):** Die Raum-Thermostate der HomematicIP-Cloud-Integration
(`climate.<raum>`, Heizgruppen mit Wandthermostat-Schaltausgang) bekommen zusätzlich das
Attribut `hvac_action` – **Heizt**, sobald ein Schaltausgang der Gruppe aktiv ist, sonst
**Untätig**. Kacheln, Thermostat-Karte und Verlaufsgrafik zeigen das wie bei anderen
Thermostaten automatisch an. Dafür erweitert die Integration die Eigenschaft `hvac_action`
der HomematicIP-Heizgruppen zur Laufzeit; Gruppen ohne Schaltausgang behalten das
Original-Verhalten, und beim Entfernen der Integration wird das Original wiederhergestellt.

## Installation (HACS)

1. HACS → ⋮ → **Benutzerdefinierte Repositories** →
   `https://github.com/ghiot/hmip-stellantriebe`, Typ **Integration**.
2. „HmIP Stellantriebe“ herunterladen, Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „HmIP Stellantriebe“.

Voraussetzung: eingerichtete Integration HomematicIP Cloud.

## Hinweis

Die Integration liest die Rohdaten (`_rawJSONData`) der homematicip-Bibliothek, weil
diese das Feld nicht selbst auswertet. Ändert sich das intern, werden die Entitäten
„nicht verfügbar“ – die Heizungsregelung selbst ist davon nie betroffen (rein lesend).

## Rechtliches

Inoffizielles Community-Projekt, nicht mit der eQ-3 AG verbunden und nicht von ihr
unterstützt. Homematic IP ist eine Marke der eQ-3 AG; der Name wird hier nur
verwendet, um die Kompatibilität zu beschreiben.
