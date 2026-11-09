"""Generate the fictional sample documents for DocuMind.

Eight documents for the fictional company "Rheintal Antriebstechnik GmbH", written in
English and German, with numbered sections and tables so that chunking and page-aware
citations actually matter. Output: data/sample_docs/ (PDF, DOCX and TXT).

Run:  python scripts/make_sample_docs.py [--out data/sample_docs]
Needs: reportlab, python-docx (both in backend dev dependencies).
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document as DocxDocument
from docx.shared import Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("make_sample_docs")

COMPANY = "Rheintal Antriebstechnik GmbH"

# A block is a tuple: ("h1" | "h2" | "p" | "bullets" | "table" | "pagebreak", payload)
Block = tuple[str, object]


@dataclass
class Doc:
    """One sample document: a title, some metadata and an ordered list of blocks."""

    filename: str
    title: str
    subtitle: str
    language: str
    blocks: list[Block] = field(default_factory=list)

    def h1(self, text: str) -> Doc:
        self.blocks.append(("h1", text))
        return self

    def h2(self, text: str) -> Doc:
        self.blocks.append(("h2", text))
        return self

    def p(self, text: str) -> Doc:
        self.blocks.append(("p", text))
        return self

    def bullets(self, *items: str) -> Doc:
        self.blocks.append(("bullets", list(items)))
        return self

    def table(self, header: list[str], *rows: list[str]) -> Doc:
        self.blocks.append(("table", [header, *rows]))
        return self

    def pagebreak(self) -> Doc:
        self.blocks.append(("pagebreak", None))
        return self


# --------------------------------------------------------------------------------------
# Document content
# --------------------------------------------------------------------------------------


def hydraulic_pump_manual() -> Doc:
    d = Doc(
        "RA-HP450_hydraulic_pump_manual.pdf",
        "RA-HP 450 Axial Piston Pump",
        "Operating and Installation Manual, Revision 3.2, March 2026",
        "en",
    )
    d.h1("1. General information")
    d.p(
        "The RA-HP 450 is a variable displacement axial piston pump for open circuit "
        "hydraulic systems in industrial presses, injection moulding machines and marine "
        "deck equipment. This manual applies to all RA-HP 450 variants with serial numbers "
        "starting with HP450-26. Keep this manual close to the machine for the whole "
        "service life of the pump."
    )
    d.h2("1.1 Intended use")
    d.p(
        "The pump is intended exclusively for pumping hydraulic fluids of the groups HLP "
        "(DIN 51524 part 2) and HEES biodegradable esters. Use with water, fuels or food "
        "liquids is not permitted. Any other use is considered improper and voids the "
        "warranty."
    )
    d.h2("1.2 Safety symbols")
    d.table(
        ["Symbol", "Meaning"],
        ["DANGER", "Immediate hazard which will result in death or serious injury."],
        ["WARNING", "Potentially hazardous situation which could result in serious injury."],
        ["CAUTION", "Situation which could result in minor injury or property damage."],
        ["NOTICE", "Information to prevent damage to the pump or the installation."],
    )
    d.pagebreak()
    d.h1("2. Technical data")
    d.table(
        ["Parameter", "Value", "Unit"],
        ["Nominal displacement", "45", "cm³/rev"],
        ["Maximum displacement", "50", "cm³/rev"],
        ["Nominal pressure", "280", "bar"],
        ["Peak pressure (max. 1 s)", "350", "bar"],
        ["Speed range", "500 to 3000", "rpm"],
        ["Maximum inlet pressure (absolute)", "0.8 to 30", "bar"],
        ["Weight (without fluid)", "38", "kg"],
        ["Permissible fluid temperature", "-20 to +80", "°C"],
        ["Viscosity range", "10 to 400", "mm²/s"],
        ["Required cleanliness class", "ISO 4406 20/18/15", "-"],
    )
    d.p(
        "The optimum operating viscosity is between 16 and 36 mm²/s. Operation below 10 mm²/s "
        "causes accelerated wear of the slipper pads and is only permitted for short periods "
        "during start-up."
    )
    d.h2("2.1 Noise emission")
    d.p(
        "At 1500 rpm and 250 bar the sound pressure level measured according to DIN 45635 is "
        "72 dB(A). At 3000 rpm the level rises to 79 dB(A). Hearing protection is mandatory "
        "when working near the running pump for more than 30 minutes per day."
    )
    d.pagebreak()
    d.h1("3. Installation")
    d.h2("3.1 Mounting position")
    d.p(
        "The pump can be installed in any position. If the shaft points upwards, the case "
        "drain line must leave the pump from the highest drain port so that the housing "
        "stays completely filled with fluid. The case drain line must end below the fluid "
        "level in the tank at all times to avoid draining the housing when the machine is "
        "stopped."
    )
    d.h2("3.2 Tightening torques")
    d.table(
        ["Connection", "Thread", "Torque (Nm)"],
        ["Mounting flange bolts", "M12 x 1.75, strength class 10.9", "110"],
        ['Pressure port flange SAE 3/4"', "M10", "57"],
        ['Suction port flange SAE 1 1/2"', "M12", "110"],
        ["Case drain port L1 / L2", "G 3/4", "160"],
        ["Pressure controller cover", "M6", "10"],
    )
    d.h2("3.3 Commissioning")
    d.p(
        "Before the first start, fill the pump housing through the upper case drain port with "
        "filtered hydraulic fluid. Start the drive at the lowest possible speed, not above "
        "500 rpm, and run the pump for at least 2 minutes at zero load. Only then increase "
        "the pressure in steps of 50 bar up to the operating pressure. Bleed the pressure "
        "line at the highest point until fluid emerges without bubbles."
    )
    d.p(
        "NOTICE: Never run the pump dry, not even for a few seconds. Dry running destroys "
        "the slipper pads within seconds and is not covered by the warranty."
    )
    d.pagebreak()
    d.h1("4. Pressure controller DR")
    d.p(
        "The pressure controller limits the maximum system pressure by reducing the swivel "
        "angle of the pump when the set pressure is reached. The factory setting is 250 bar. "
        "The setting range is 50 to 280 bar. One full turn of the adjustment screw changes "
        "the pressure by approximately 55 bar. Turning clockwise increases the pressure. "
        "After adjustment, secure the screw with the lock nut and tighten the nut to 10 Nm."
    )
    d.h1("5. Maintenance intervals")
    d.table(
        ["Interval", "Activity"],
        ["Daily", "Check fluid level, listen for unusual noise, look for external leakage."],
        ["Weekly", "Check the filter clogging indicator and the fluid temperature."],
        ["Every 500 operating hours", "Take an oil sample and check cleanliness class."],
        ["Every 2000 operating hours or 12 months", "Replace the suction and return filters."],
        ["Every 4000 operating hours", "Check the shaft seal and the mounting bolt torques."],
        ["Every 12000 operating hours", "Major overhaul by RA service or an authorised partner."],
    )
    d.p(
        "The shaft seal is a wear part. A leakage of up to 3 drops per hour at the shaft seal "
        "is normal and does not require any action."
    )
    d.pagebreak()
    d.h1("6. Troubleshooting")
    d.table(
        ["Symptom", "Possible cause", "Remedy"],
        [
            "Pump does not deliver flow",
            "Wrong direction of rotation",
            "Compare the arrow on the housing with the motor rotation and swap two phases.",
        ],
        [
            "Loud knocking noise, foam in the tank",
            "Air in the suction line (cavitation)",
            "Check suction line for leaks, reduce suction height, check fluid level.",
        ],
        [
            "Pressure does not reach the set value",
            "Pressure controller worn or wrongly set",
            "Readjust controller, replace the controller cartridge if the setting drifts.",
        ],
        [
            "Fluid temperature above 80 °C",
            "Cooler dirty or pressure relief valve opening permanently",
            "Clean the cooler, check the relief valve setting (must be above the DR setting).",
        ],
        [
            "Leakage at the shaft, more than 3 drops per hour",
            "Shaft seal worn or case pressure above 2 bar",
            "Check the case drain line for restrictions, replace the shaft seal.",
        ],
    )
    d.h1("7. Spare parts")
    d.table(
        ["Part number", "Description", "Notes"],
        ["HP450-SK-01", "Seal kit complete", "Includes shaft seal and all O-rings"],
        ["HP450-DR-250", "Pressure controller cartridge DR", "Pre-set to 250 bar"],
        ["HP450-SP-09", "Slipper pad set (9 pieces)", "Replace only as a complete set"],
        ["HP450-BR-02", "Bearing set", "Requires press tool HP-T-11"],
    )
    d.p(
        "Technical support: service@rheintal-antriebstechnik.example, +49 7621 555 0450, "
        "Monday to Friday 7:00 to 17:00 CET."
    )
    return d


def power_supply_manual() -> Doc:
    d = Doc(
        "RA-PS2440_Netzteil_Handbuch.pdf",
        "RA-PS 24/40 Schaltnetzteil",
        "Betriebsanleitung, Version 2.1, Februar 2026",
        "de",
    )
    d.h1("1. Allgemeines")
    d.p(
        "Das RA-PS 24/40 ist ein primär getaktetes Schaltnetzteil für die Montage auf "
        "Tragschienen nach DIN EN 60715 (TS 35). Es versorgt Steuerungen, Sensoren und "
        "Aktoren in Industrieanlagen mit einer geregelten Gleichspannung von 24 V DC und "
        "einem Nennstrom von 40 A. Diese Anleitung richtet sich an Elektrofachkräfte."
    )
    d.h2("1.1 Bestimmungsgemäße Verwendung")
    d.p(
        "Das Gerät darf nur in geschlossenen Schaltschränken mit mindestens Schutzart IP20 "
        "betrieben werden. Der Einsatz in explosionsgefährdeten Bereichen (ATEX) ist nicht "
        "zulässig. Für medizinische Anwendungen nach IEC 60601 ist das Gerät nicht zugelassen."
    )
    d.pagebreak()
    d.h1("2. Technische Daten")
    d.table(
        ["Kenngröße", "Wert"],
        ["Eingangsspannung", "3 AC 400 bis 500 V, -15 % / +10 %"],
        ["Eingangsfrequenz", "50 bis 60 Hz"],
        ["Ausgangsspannung", "24 V DC, einstellbar 22,5 bis 28,5 V"],
        ["Ausgangsnennstrom", "40 A bei 24 V"],
        ["Power Boost", "60 A für maximal 5 s"],
        ["Wirkungsgrad", "typisch 94,5 % bei Volllast"],
        ["Leerlaufverluste", "< 8 W"],
        ["Umgebungstemperatur Betrieb", "-25 °C bis +70 °C, Derating ab +55 °C"],
        ["Derating", "2,5 % pro K oberhalb 55 °C"],
        ["Schutzart", "IP20"],
        ["Abmessungen (B x H x T)", "125 x 130 x 150 mm"],
        ["Gewicht", "2,1 kg"],
        ["MTBF nach IEC 61709 bei 40 °C", "> 900 000 h"],
    )
    d.p(
        "Die Ausgangsspannung wird werkseitig auf 24,2 V eingestellt. Mit dem Potentiometer "
        "auf der Frontseite kann sie zwischen 22,5 V und 28,5 V verändert werden, um "
        "Leitungsverluste bei langen Leitungen auszugleichen."
    )
    d.pagebreak()
    d.h1("3. Montage und Anschluss")
    d.h2("3.1 Einbaulage und Abstände")
    d.p(
        "Das Gerät ist senkrecht so zu montieren, dass die Anschlussklemmen für den Eingang "
        "unten liegen. Zur Kühlung müssen oberhalb und unterhalb des Geräts mindestens 50 mm "
        "und seitlich mindestens 15 mm Abstand frei bleiben. Bei seitlichem Abstand unter "
        "15 mm reduziert sich der zulässige Dauerstrom auf 32 A."
    )
    d.h2("3.2 Anschlusswerte")
    d.table(
        ["Klemme", "Leiterquerschnitt", "Anzugsdrehmoment"],
        ["Eingang L1, L2, L3, PE", "0,5 bis 6 mm²", "0,8 Nm"],
        ["Ausgang +, + , -, -", "0,5 bis 16 mm²", "1,5 Nm"],
        ["Signalkontakt DC OK (13, 14)", "0,2 bis 2,5 mm²", "0,5 Nm"],
    )
    d.h2("3.3 Absicherung")
    d.p(
        "Eingangsseitig ist ein Leitungsschutzschalter mit Charakteristik C und 10 A oder 16 A "
        "vorzusehen. Ausgangsseitig empfehlen wir Sicherungsautomaten oder elektronische "
        "Sicherungen vom Typ RA-EF 24, damit bei einem Kurzschluss in einem Zweig die "
        "übrigen Verbraucher weiter versorgt werden."
    )
    d.pagebreak()
    d.h1("4. Signalisierung")
    d.table(
        ["LED", "Zustand", "Bedeutung"],
        ["DC OK grün", "leuchtet", "Ausgangsspannung größer als 21,5 V"],
        ["DC OK grün", "blinkt", "Power Boost aktiv, Ausgang überlastet"],
        ["DC OK grün", "aus", "Keine Ausgangsspannung oder Spannung unter 21,5 V"],
        ["Overload rot", "leuchtet", "Überlast seit mehr als 5 s, Strombegrenzung aktiv"],
        ["Temp rot", "blinkt", "Übertemperatur, Gerät schaltet bei 85 °C intern ab"],
    )
    d.p(
        "Der potentialfreie Signalkontakt DC OK (Klemmen 13 und 14) ist geschlossen, solange "
        "die Ausgangsspannung über 21,5 V liegt. Er ist für maximal 30 V DC und 1 A ausgelegt."
    )
    d.h1("5. Parallelbetrieb")
    d.p(
        "Bis zu vier Geräte RA-PS 24/40 können zur Leistungserhöhung parallel geschaltet "
        "werden. Dazu ist der Schalter auf der Frontseite auf 'Parallel' zu stellen und die "
        "Ausgangsspannung aller Geräte auf den gleichen Wert, Toleranz 50 mV, einzustellen. "
        "Zur Redundanz (1+1) ist je Gerät ein Entkopplungsmodul RA-DM 40 erforderlich."
    )
    d.pagebreak()
    d.h1("6. Fehlersuche")
    d.table(
        ["Fehlerbild", "Ursache", "Abhilfe"],
        [
            "Keine Ausgangsspannung, alle LEDs aus",
            "Eingangsspannung fehlt oder unter 340 V",
            "Netzzuleitung und Sicherung prüfen.",
        ],
        [
            "Overload leuchtet dauerhaft",
            "Last über 40 A oder Kurzschluss am Ausgang",
            "Verbraucher abklemmen, Strom je Zweig messen.",
        ],
        [
            "Temp blinkt",
            "Umgebungstemperatur zu hoch oder Abstände nicht eingehalten",
            "Belüftung prüfen, Abstand von 50 mm oben und unten sicherstellen.",
        ],
        [
            "Ausgangsspannung schwankt",
            "Parallelbetrieb ohne Abgleich",
            "Spannungen auf 50 mV abgleichen, Schalter auf Parallel.",
        ],
    )
    d.h1("7. Entsorgung und Zulassungen")
    d.p(
        "Das Gerät trägt die CE-Kennzeichnung nach der Niederspannungsrichtlinie 2014/35/EU "
        "und der EMV-Richtlinie 2014/30/EU. Es erfüllt UL 61010-1 und ist nach IEC 62368-1 "
        "geprüft. Altgeräte sind gemäß WEEE-Richtlinie über den Hersteller zurückzugeben; "
        "die WEEE-Registrierungsnummer lautet DE 55123498."
    )
    return d


def supplier_contract() -> Doc:
    d = Doc(
        "Rahmenliefervertrag_Lieferanten.docx",
        "Rahmenliefervertrag",
        f"zwischen {COMPANY}, Lörrach (Auftraggeber) und dem Lieferanten, Stand 01.01.2026",
        "de",
    )
    d.h1("§ 1 Vertragsgegenstand")
    d.p(
        "Dieser Rahmenliefervertrag regelt die Lieferung von Zukaufteilen, Baugruppen und "
        "Rohmaterial durch den Lieferanten an den Auftraggeber. Die einzelnen Lieferungen "
        "werden durch Einzelabrufe (Bestellungen) ausgelöst. Allgemeine Geschäftsbedingungen "
        "des Lieferanten finden keine Anwendung, auch wenn der Auftraggeber ihnen nicht "
        "ausdrücklich widerspricht."
    )
    d.h1("§ 2 Vertragslaufzeit und Kündigung")
    d.p(
        "Der Vertrag beginnt am 01.01.2026 und hat eine feste Laufzeit von 36 Monaten. Er "
        "verlängert sich jeweils um weitere 12 Monate, wenn er nicht mit einer Frist von "
        "6 Monaten zum Ende der Laufzeit schriftlich gekündigt wird. Das Recht zur "
        "außerordentlichen Kündigung aus wichtigem Grund bleibt unberührt, insbesondere bei "
        "Eröffnung eines Insolvenzverfahrens über das Vermögen einer Partei."
    )
    d.h1("§ 3 Bestellungen und Abrufe")
    d.p(
        "Bestellungen erfolgen schriftlich über das Lieferantenportal oder per E-Mail. Der "
        "Lieferant bestätigt jede Bestellung innerhalb von 3 Arbeitstagen. Erfolgt keine "
        "Bestätigung, gilt die Bestellung als zu den Bedingungen des Auftraggebers angenommen. "
        "Mengenänderungen von bis zu 20 Prozent gegenüber der Vorschau sind bis 4 Wochen vor "
        "dem Liefertermin kostenneutral möglich."
    )
    d.h1("§ 4 Preise und Zahlungsbedingungen")
    d.p(
        "Die vereinbarten Preise sind Festpreise in Euro, verstehen sich zuzüglich der "
        "gesetzlichen Umsatzsteuer und gelten DAP Werk Lörrach (Incoterms 2020) einschließlich "
        "Verpackung. Preisanpassungen sind frühestens nach 12 Monaten und nur bei einer "
        "nachgewiesenen Veränderung der Materialkosten um mehr als 5 Prozent möglich."
    )
    d.table(
        ["Zahlungsziel", "Konditionen"],
        ["14 Tage", "3 % Skonto"],
        ["30 Tage", "2 % Skonto"],
        ["60 Tage", "netto"],
    )
    d.p(
        "Rechnungen sind elektronisch im Format ZUGFeRD 2.x oder XRechnung an "
        "rechnungseingang@rheintal-antriebstechnik.example zu senden. Die Zahlungsfrist "
        "beginnt mit dem Eingang einer prüffähigen Rechnung, frühestens jedoch mit dem "
        "Wareneingang."
    )
    d.h1("§ 5 Lieferung, Liefertermine und Verzug")
    d.p(
        "Vereinbarte Liefertermine sind verbindlich. Maßgeblich ist der Wareneingang im Werk "
        "Lörrach. Bei Lieferverzug ist der Auftraggeber berechtigt, eine Vertragsstrafe von "
        "0,5 Prozent des Nettoauftragswertes der verspäteten Lieferung pro angefangener Woche, "
        "höchstens jedoch 5 Prozent, zu verlangen. Weitergehende Schadensersatzansprüche "
        "bleiben vorbehalten; die Vertragsstrafe wird darauf angerechnet."
    )
    d.h1("§ 6 Qualität und Wareneingangsprüfung")
    d.p(
        "Der Lieferant unterhält ein Qualitätsmanagementsystem nach ISO 9001 und strebt die "
        "Zertifizierung nach IATF 16949 an. Jeder Lieferung ist ein Prüfzeugnis 3.1 nach "
        "EN 10204 beizufügen, soweit in der Zeichnung gefordert. Der Auftraggeber prüft die "
        "Ware im Wareneingang nur auf Identität, Menge und offensichtliche Transportschäden. "
        "Die Rüge offener Mängel erfolgt innerhalb von 10 Arbeitstagen nach Wareneingang, die "
        "Rüge versteckter Mängel innerhalb von 10 Arbeitstagen nach Entdeckung."
    )
    d.h1("§ 7 Gewährleistung")
    d.p(
        "Die Gewährleistungsfrist beträgt 24 Monate ab Wareneingang beim Auftraggeber. Für "
        "Teile, die in Anlagen des Auftraggebers verbaut und an Endkunden ausgeliefert "
        "werden, beträgt die Frist 36 Monate ab Wareneingang, höchstens jedoch 30 Monate ab "
        "Inbetriebnahme beim Endkunden. Im Falle eines Mangels hat der Auftraggeber die Wahl "
        "zwischen Nachbesserung und Ersatzlieferung. Schlägt die Nacherfüllung zweimal fehl, "
        "kann der Auftraggeber vom Einzelabruf zurücktreten und Schadensersatz verlangen."
    )
    d.h1("§ 8 Haftung und Versicherung")
    d.p(
        "Der Lieferant unterhält eine Betriebs- und Produkthaftpflichtversicherung mit einer "
        "Deckungssumme von mindestens 5 Millionen Euro je Schadensfall und weist diese auf "
        "Verlangen nach. Rückrufkosten trägt der Lieferant, soweit der Rückruf auf einem "
        "Mangel seiner Lieferung beruht."
    )
    d.h1("§ 9 Geheimhaltung und Compliance")
    d.p(
        "Beide Parteien behandeln alle technischen und kaufmännischen Informationen der "
        "anderen Partei vertraulich. Die Geheimhaltungspflicht gilt für 5 Jahre nach "
        "Vertragsende. Der Lieferant verpflichtet sich zur Einhaltung des Verhaltenskodex für "
        "Lieferanten des Auftraggebers sowie der Anforderungen des "
        "Lieferkettensorgfaltspflichtengesetzes (LkSG)."
    )
    d.h1("§ 10 Schlussbestimmungen")
    d.p(
        "Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des UN-Kaufrechts "
        "(CISG). Ausschließlicher Gerichtsstand ist Freiburg im Breisgau. Änderungen dieses "
        "Vertrages bedürfen der Schriftform. Sollte eine Bestimmung unwirksam sein, bleibt "
        "die Wirksamkeit der übrigen Bestimmungen unberührt."
    )
    return d


def warranty_policy() -> Doc:
    d = Doc(
        "Warranty_Policy_Products.docx",
        "Product Warranty Policy",
        "Applies to all products sold by Rheintal Antriebstechnik GmbH, valid from 1 January 2026",
        "en",
    )
    d.h1("1. Scope")
    d.p(
        "This policy describes the warranty that Rheintal Antriebstechnik GmbH grants to "
        "business customers for hydraulic pumps, motors, valves, power supplies and drive "
        "electronics. It supplements the statutory warranty rights and the General Terms of "
        "Sale; where the two conflict, an individually negotiated contract prevails."
    )
    d.h1("2. Warranty periods")
    d.table(
        ["Product group", "Standard warranty", "Extended warranty (optional)"],
        ["Hydraulic pumps and motors", "24 months from delivery", "36 months, surcharge 4 %"],
        ["Industrial valves", "24 months from delivery", "36 months, surcharge 3 %"],
        ["Power supplies (RA-PS series)", "36 months from delivery", "60 months, surcharge 6 %"],
        ["Drive electronics and controllers", "24 months from delivery", "not available"],
        ["Spare parts and repairs", "12 months from delivery", "not available"],
    )
    d.p(
        "The warranty period starts on the date of delivery as stated on the delivery note. "
        "The extended warranty must be ordered together with the product; it cannot be "
        "purchased afterwards. The warranty period is not extended by a repair or replacement, "
        "except that replaced parts carry a warranty of 12 months if the remaining period is "
        "shorter."
    )
    d.h1("3. What is covered")
    d.p(
        "Rheintal Antriebstechnik GmbH warrants that products are free from defects in "
        "material and workmanship under normal use as described in the product manual. "
        "Covered remedies are, at our choice, repair at our service centre in Lörrach, "
        "delivery of a replacement product, or a refund of the purchase price."
    )
    d.h1("4. What is not covered")
    d.bullets(
        "Normal wear of wear parts such as shaft seals, filters, slipper pads and fans.",
        "Damage caused by contaminated fluid outside cleanliness class ISO 4406 20/18/15.",
        "Dry running, cavitation, operation outside the specified temperature or pressure.",
        "Modifications, repairs or openings of the product by non-authorised persons.",
        "Damage from incorrect installation, wiring faults, overvoltage or lightning.",
        "Cosmetic damage that does not affect function.",
        "Consequential damages such as production downtime or loss of profit.",
    )
    d.h1("5. How to make a claim")
    d.p(
        "Report the defect through the customer portal or by e-mail to "
        "warranty@rheintal-antriebstechnik.example within 14 days of discovering it. Provide "
        "the serial number, the delivery note number, a description of the fault and, where "
        "possible, photos or an oil analysis report. Our service team issues a Return "
        "Material Authorisation (RMA) number within 2 working days. Products returned without "
        "an RMA number cannot be processed."
    )
    d.p(
        "Return the product in its original or equivalent packaging, drained of fluid, with "
        "the RMA number visible on the outside. Shipping costs for justified warranty claims "
        "are refunded; for unjustified claims an inspection fee of EUR 180 plus return "
        "shipping is charged."
    )
    d.h1("6. Processing time")
    d.p(
        "Standard warranty repairs are completed within 10 working days after receipt of the "
        "product. For customers with a service contract of level 'Silver' or higher an "
        "advance replacement unit is shipped within 48 hours."
    )
    d.h1("7. Contact")
    d.p(
        "Warranty department, Rheintal Antriebstechnik GmbH, Industriestraße 14, 79539 "
        "Lörrach, Germany. Phone +49 7621 555 0300, Monday to Friday 8:00 to 16:30 CET."
    )
    return d


def it_security_guideline() -> Doc:
    d = Doc(
        "IT_Security_Guideline.pdf",
        "IT Security Guideline for Employees",
        "Document ID ISG-2026-01, approved by the CISO, effective 1 February 2026",
        "en",
    )
    d.h1("1. Purpose and scope")
    d.p(
        "This guideline defines the minimum security rules for everyone who uses IT systems "
        "of Rheintal Antriebstechnik GmbH: employees, working students, interns and external "
        "contractors. It implements the requirements of ISO/IEC 27001 and the TISAX "
        "assessment level 2. Violations may lead to disciplinary action."
    )
    d.h1("2. Passwords and authentication")
    d.table(
        ["Rule", "Requirement"],
        ["Minimum password length", "14 characters"],
        ["Complexity", "At least three of: upper case, lower case, digits, symbols"],
        ["Rotation", "No forced rotation; change immediately if compromise is suspected"],
        ["Reuse", "The last 10 passwords cannot be reused"],
        ["Multi-factor authentication", "Mandatory for VPN, e-mail, ERP and all cloud services"],
        ["Password manager", "Only the company-approved manager (Bitwarden Teams)"],
    )
    d.p(
        "Passwords must never be shared, written on paper or stored in browsers. Shared "
        "accounts are prohibited except for documented technical service accounts owned by "
        "IT Operations."
    )
    d.pagebreak()
    d.h1("3. Devices and remote work")
    d.p(
        "Only company-managed devices enrolled in the mobile device management system may "
        "access internal systems. Devices lock automatically after 5 minutes of inactivity. "
        "Hard disks are encrypted with BitLocker or FileVault. Private USB storage devices "
        "are blocked; approved encrypted USB sticks can be requested from the IT service desk."
    )
    d.p(
        "When working remotely, always connect through the company VPN. Public Wi-Fi may "
        "only be used with the VPN active. Confidential documents must not be printed at home "
        "or in hotels."
    )
    d.h1("4. E-mail and phishing")
    d.p(
        "Check the sender address and hover over links before clicking. Report suspicious "
        "e-mails with the 'Report Phishing' button in Outlook; do not forward them. Never "
        "open macros in Office documents from external senders. The IT service desk will "
        "never ask for your password by e-mail or phone."
    )
    d.h1("5. Data classification")
    d.table(
        ["Class", "Examples", "Handling"],
        ["Public", "Brochures, published data sheets", "No restrictions"],
        [
            "Internal",
            "Organisation charts, process descriptions",
            "Company network and MDM devices",
        ],
        ["Confidential", "Drawings, prices, customer data", "Encrypted storage and transfer"],
        [
            "Strictly confidential",
            "M&A documents, source code of control firmware",
            "Named access list, no cloud storage, no printing",
        ],
    )
    d.pagebreak()
    d.h1("6. Use of AI tools")
    d.p(
        "Public AI chat services may be used for public and internal information only. "
        "Confidential or strictly confidential data, personal data and customer drawings must "
        "not be entered into public AI services. For such data use the internal DocuMind "
        "assistant, which runs on company infrastructure. Generated code must be reviewed "
        "before it is committed."
    )
    d.h1("7. Incident reporting")
    d.p(
        "Report any suspected security incident, lost device or data leak immediately to the "
        "IT service desk at extension 4444 or security@rheintal-antriebstechnik.example, at "
        "the latest within 24 hours. Lost or stolen devices are wiped remotely. Do not try to "
        "investigate incidents yourself."
    )
    d.h1("8. Software and updates")
    d.p(
        "Only software from the company software portal may be installed. Security updates "
        "are installed automatically; devices that have not been updated for more than 30 days "
        "lose network access until they are patched. Local administrator rights are granted "
        "only on request for a maximum of 90 days."
    )
    d.h1("9. Review")
    d.p(
        "This guideline is reviewed annually by the information security officer. The next "
        "review is due in February 2027."
    )
    return d


def travel_expense_policy() -> Doc:
    d = Doc(
        "Reisekostenrichtlinie.docx",
        "Reisekostenrichtlinie",
        "Gültig für alle Mitarbeitenden der Rheintal Antriebstechnik GmbH ab 01.01.2026",
        "de",
    )
    d.h1("1. Geltungsbereich")
    d.p(
        "Diese Richtlinie regelt die Genehmigung, Buchung und Abrechnung von Dienstreisen "
        "aller Mitarbeitenden einschließlich Werkstudierender und Auszubildender. Eine "
        "Dienstreise liegt vor, wenn die Tätigkeit außerhalb der ersten Tätigkeitsstätte "
        "ausgeübt wird und die Entfernung mehr als 20 km beträgt."
    )
    d.h1("2. Genehmigung")
    d.p(
        "Dienstreisen im Inland sind vor Reisebeginn durch die direkte Führungskraft im "
        "Reisetool zu genehmigen. Auslandsreisen müssen zusätzlich von der Bereichsleitung "
        "genehmigt werden. Reisen mit voraussichtlichen Gesamtkosten über 2 500 Euro "
        "benötigen die Freigabe der Geschäftsführung. Der Antrag ist mindestens 5 Arbeitstage "
        "vor Reisebeginn zu stellen."
    )
    d.h1("3. Verkehrsmittel")
    d.table(
        ["Verkehrsmittel", "Regelung"],
        ["Bahn", "2. Klasse; 1. Klasse ab 3 Stunden Fahrzeit oder für Führungskräfte"],
        ["Flug", "Economy; Business Class nur bei Flügen über 6 Stunden"],
        ["Mietwagen", "Kompaktklasse; Mittelklasse ab 3 Reisenden oder mit Gepäck über 50 kg"],
        ["Privat-Pkw", "0,30 Euro je Kilometer, ab dem 21. Kilometer; max. 400 km pro Fahrt"],
        ["Taxi", "Nur wenn kein ÖPNV zumutbar ist oder vor 6:00 Uhr bzw. nach 22:00 Uhr"],
    )
    d.p(
        "Bahnfahrten sind bevorzugt über das Firmenkonto mit der BahnCard Business 50 zu "
        "buchen. Für Flüge innerhalb Deutschlands ist eine Begründung erforderlich, warum die "
        "Bahn nicht genutzt werden konnte."
    )
    d.h1("4. Übernachtung")
    d.p(
        "Hotels werden über das Reisetool gebucht. Die Obergrenze beträgt 120 Euro pro Nacht "
        "inklusive Frühstück. In München, Frankfurt am Main, Hamburg und Düsseldorf sowie "
        "während Messen gilt eine Obergrenze von 180 Euro. Bei privater Übernachtung wird "
        "eine Pauschale von 20 Euro pro Nacht gezahlt."
    )
    d.h1("5. Verpflegungsmehraufwand")
    d.table(
        ["Abwesenheit", "Pauschale Inland"],
        ["mehr als 8 Stunden", "14 Euro"],
        ["An- und Abreisetag bei mehrtägigen Reisen", "14 Euro"],
        ["24 Stunden", "28 Euro"],
    )
    d.p(
        "Wird vom Arbeitgeber oder Dritten eine Mahlzeit gestellt, wird die Pauschale "
        "gekürzt: Frühstück um 20 Prozent, Mittag- und Abendessen jeweils um 40 Prozent der "
        "Tagespauschale von 28 Euro. Für Auslandsreisen gelten die vom Bundesfinanzministerium "
        "veröffentlichten Länderpauschalen."
    )
    d.h1("6. Bewirtung und sonstige Kosten")
    d.p(
        "Geschäftliche Bewirtungen sind bis 60 Euro pro Person erstattungsfähig und müssen "
        "auf dem Bewirtungsbeleg Anlass und Teilnehmende nennen. Parkgebühren, Gepäckgebühren "
        "und Internetkosten im Hotel werden gegen Beleg erstattet. Minibar, Pay-TV und "
        "Bußgelder werden nicht erstattet."
    )
    d.h1("7. Abrechnung")
    d.p(
        "Die Reisekostenabrechnung ist innerhalb von 4 Wochen nach Reiseende im Reisetool "
        "einzureichen. Belege werden als Foto oder Scan hochgeladen; Originalbelege sind "
        "3 Monate aufzubewahren. Die Erstattung erfolgt mit der nächsten Gehaltsabrechnung, "
        "spätestens jedoch 30 Tage nach Freigabe. Abrechnungen, die später als 6 Monate nach "
        "Reiseende eingereicht werden, können nicht mehr erstattet werden."
    )
    d.h1("8. Ansprechpartner")
    d.p(
        "Fragen beantwortet das Team Reisemanagement unter reisen@rheintal-antriebstechnik.example "
        "oder Durchwahl 2210."
    )
    return d


def onboarding_guide() -> Doc:
    d = Doc(
        "Onboarding_Guide_New_Employees.txt",
        "Onboarding Guide for New Employees",
        "People & Culture team, edition 2026",
        "en",
    )
    d.h1("1. Welcome")
    d.p(
        "Welcome to Rheintal Antriebstechnik GmbH. We are a family-owned company founded in "
        "1961 in Lörrach with around 850 employees at three sites: Lörrach (headquarters and "
        "hydraulics plant), Weil am Rhein (power electronics) and Brno in the Czech Republic "
        "(assembly). This guide walks you through your first 90 days."
    )
    d.h1("2. Your first day")
    d.p(
        "Please arrive at the main reception, Industriestraße 14, at 9:00. Bring your ID card, "
        "your tax identification number, your social security card and your bank details. "
        "You will receive your employee badge, your laptop and your locker key. The badge "
        "opens the doors from 6:00 to 20:00; outside these hours a request to Facility "
        "Management is required."
    )
    d.h1("3. Working hours and time recording")
    d.p(
        "Full-time employees work 35 hours per week under the collective agreement. Core "
        "working hours are 9:00 to 15:00 on Monday to Thursday and 9:00 to 13:00 on Friday. "
        "Flexitime is possible between 6:00 and 20:00. Working time is recorded in the HR "
        "portal; the flexitime account may not exceed plus 40 or minus 20 hours. Working "
        "students may work a maximum of 20 hours per week during the lecture period and up to "
        "40 hours during semester breaks."
    )
    d.h1("4. Remote work")
    d.p(
        "After the probation period of 6 months, employees may work remotely up to 2 days per "
        "week, agreed with their manager. Working students can work remotely from day one on "
        "days without on-site tasks. Remote work from abroad requires HR approval and is "
        "limited to 20 days per year within the EU."
    )
    d.h1("5. Vacation and absence")
    d.table(
        ["Topic", "Rule"],
        ["Vacation days", "30 days per year for full-time, pro rata for part-time"],
        ["Carry-over", "Remaining days must be taken by 31 March of the following year"],
        ["Sick leave", "Inform your manager before 9:00; certificate needed from day 3"],
        ["Special leave", "1 day for moving, 2 days for own wedding, 2 days for a bereavement"],
    )
    d.h1("6. IT and accounts")
    d.p(
        "Your Microsoft 365 account is ready on your first day. Set up multi-factor "
        "authentication with the Microsoft Authenticator app before you leave on day one. "
        "The IT service desk is reachable at extension 4444 from 7:00 to 17:00. Please read "
        "the IT Security Guideline in your first week and complete the security e-learning "
        "within 30 days."
    )
    d.h1("7. Training in the first 90 days")
    d.bullets(
        "Week 1: company tour, safety briefing, introduction to the ERP system.",
        "Week 2 to 4: shadowing in your team, first small tasks, meet your buddy weekly.",
        "Day 30: first feedback talk with your manager.",
        "Day 60: completion of mandatory e-learnings (security, compliance, data protection).",
        "Day 90: probation review and goal setting for the rest of the year.",
    )
    d.h1("8. Benefits")
    d.p(
        "Employees receive a subsidised canteen lunch for 4.20 Euro, a JobRad bicycle leasing "
        "offer, a company pension contribution of 50 Euro per month and the Deutschlandticket "
        "job ticket with a 30 Euro subsidy. Working students receive the canteen subsidy and "
        "the job ticket subsidy but no pension contribution."
    )
    d.h1("9. Who to ask")
    d.table(
        ["Topic", "Contact"],
        ["Contract, payroll, certificates", "People & Culture, extension 2100"],
        ["Laptop, accounts, software", "IT service desk, extension 4444"],
        ["Badge, parking, lockers", "Facility Management, extension 3300"],
        ["Travel bookings", "Travel management, extension 2210"],
    )
    return d


def maintenance_procedure() -> Doc:
    d = Doc(
        "Maintenance_Procedure_Hydraulic_Test_Bench.pdf",
        "Maintenance Procedure MP-07: Hydraulic Test Bench HTB-3",
        "Work instruction, revision D, owner: Maintenance department, valid from 15 January 2026",
        "en",
    )
    d.h1("1. Purpose")
    d.p(
        "This procedure describes the preventive maintenance of the hydraulic test bench HTB-3 "
        "in hall 2, used for end-of-line testing of RA-HP pumps. Following it keeps the "
        "measurement uncertainty within the limits required by the ISO 9001 test plan and "
        "prevents unplanned downtime."
    )
    d.h1("2. Responsibilities and qualification")
    d.p(
        "Preventive maintenance may only be carried out by maintenance technicians who have "
        "completed the HTB-3 training module and the annual hydraulics safety refresher. "
        "Electrical work on the 400 V drive cabinet is reserved for qualified electricians. "
        "The shift supervisor releases the bench for maintenance in the CMMS and signs the "
        "lockout tag."
    )
    d.pagebreak()
    d.h1("3. Safety: lockout and depressurising")
    d.bullets(
        "Switch off the main drive (160 kW motor) at the main switch Q1 and lock it with a "
        "personal padlock.",
        "Open the accumulator discharge valve V12 and wait until the pressure gauge PI-3 "
        "shows 0 bar.",
        "Wait at least 10 minutes after switching off before opening any hydraulic "
        "connection; the fluid may be up to 70 °C.",
        "Wear safety glasses, nitrile gloves and safety shoes. Hearing protection is "
        "required while the bench is running.",
        "Place absorbent mats under every connection that is opened. Spilled fluid is a "
        "slip hazard.",
    )
    d.h1("4. Maintenance schedule")
    d.table(
        ["Interval", "Task", "Duration"],
        [
            "Weekly",
            "Visual leak check, check fluid level in the 1200 l tank, clean the test area",
            "20 min",
        ],
        [
            "Monthly",
            "Check filter clogging indicators, test the emergency stop, calibrate PI-1 to "
            "PI-4 zero point",
            "1 h",
        ],
        [
            "Quarterly",
            "Oil sample for cleanliness and water content, check accumulator pre-charge pressure",
            "2 h",
        ],
        [
            "Semi-annually",
            "Replace pressure filter F1 and return filter F2, check hose assemblies",
            "3 h",
        ],
        [
            "Annually",
            "Replace all hoses older than 6 years, calibrate flow meter FT-1 and torque "
            "sensor, oil change",
            "8 h",
        ],
    )
    d.pagebreak()
    d.h1("5. Detailed steps")
    d.h2("5.1 Oil sample (quarterly)")
    d.p(
        "Take the sample while the bench is running at operating temperature from the sampling "
        "valve SV-1 in the return line, after flushing 200 ml. Use the laboratory bottles "
        "from the stores (article 77-0931). Acceptance limits: cleanliness class ISO 4406 "
        "18/16/13 and water content below 300 ppm. If a limit is exceeded, run the offline "
        "filter unit for 24 hours and repeat the sample."
    )
    d.h2("5.2 Accumulator pre-charge (quarterly)")
    d.p(
        "The 50 l bladder accumulator must be pre-charged with nitrogen to 90 bar at 20 °C. "
        "Check with the charging and testing device RA-FPU after depressurising the hydraulic "
        "side. A pre-charge below 80 bar means the bladder is leaking; replace the bladder and "
        "record the serial number in the CMMS. Never use oxygen or compressed air for pre-charging."
    )
    d.h2("5.3 Filter replacement (semi-annually)")
    d.p(
        "Pressure filter F1 uses element RA-FE 10/25 (10 micron absolute). Return filter F2 uses "
        "element RA-FE 10/60. Lubricate the O-rings with hydraulic fluid before fitting. Tighten "
        "the filter bowl by hand plus a quarter turn. After the restart, check the clogging "
        "indicator; it must show green at operating temperature."
    )
    d.h2("5.4 Flow meter calibration (annually)")
    d.p(
        "The turbine flow meter FT-1 is calibrated against the reference gear meter at five "
        "points between 20 and 200 l/min. The permissible deviation is 0.5 percent of the "
        "measured value. Record the calibration in the test equipment database and apply a new "
        "calibration label. If the deviation exceeds 0.5 percent, send the meter to the "
        "manufacturer; the spare meter from cabinet S4 is used in the meantime."
    )
    d.pagebreak()
    d.h1("6. Restart and release")
    d.p(
        "Remove all tools and mats, close valve V12, remove the lockout and switch on Q1. Run the "
        "bench for 5 minutes at minimum pressure and check for leaks. Then run the reference "
        "pump HP450-REF and compare flow and pressure with the reference values; the deviation "
        "must be below 2 percent. Record the maintenance in the CMMS work order and inform the "
        "shift supervisor, who releases the bench for production."
    )
    d.h1("7. Records")
    d.table(
        ["Record", "Where", "Retention"],
        ["Maintenance work order", "CMMS", "10 years"],
        ["Oil analysis report", "Quality drive, folder HTB-3", "10 years"],
        [
            "Calibration certificate FT-1",
            "Test equipment database",
            "Until next calibration + 5 years",
        ],
        ["Hose replacement list", "CMMS asset HTB-3", "Life of the bench"],
    )
    return d


ALL_DOCS = [
    hydraulic_pump_manual,
    power_supply_manual,
    supplier_contract,
    warranty_policy,
    it_security_guideline,
    travel_expense_policy,
    onboarding_guide,
    maintenance_procedure,
]


# --------------------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------------------


def _pdf_footer(canvas, doc) -> None:  # noqa: ANN001 - reportlab callback signature
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(20 * mm, 12 * mm, COMPANY)
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_pdf(doc: Doc, path: Path) -> None:
    """Render a Doc to PDF with reportlab platypus (real text, so pypdf can extract it)."""
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=20, spaceAfter=6)
    subtitle_style = ParagraphStyle(
        "DocSubtitle", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.grey
    )
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)
    cell = ParagraphStyle("Cell", parent=body, fontSize=9, leading=11, spaceAfter=0)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceBefore=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=6)

    story = [
        Paragraph(doc.title, title_style),
        Paragraph(doc.subtitle, subtitle_style),
        Paragraph(COMPANY, subtitle_style),
        Spacer(1, 10 * mm),
    ]
    for kind, payload in doc.blocks:
        if kind == "h1":
            story.append(Paragraph(str(payload), h1))
        elif kind == "h2":
            story.append(Paragraph(str(payload), h2))
        elif kind == "p":
            story.append(Paragraph(str(payload), body))
        elif kind == "bullets":
            for item in payload:  # type: ignore[union-attr]
                story.append(Paragraph(f"• {item}", body))
        elif kind == "table":
            rows = [[Paragraph(c, cell) for c in row] for row in payload]  # type: ignore[union-attr]
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2EC")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.extend([table, Spacer(1, 4 * mm)])
        elif kind == "pagebreak":
            story.append(PageBreak())

    pdf = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=doc.title,
        author=COMPANY,
    )
    pdf.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)


def render_docx(doc: Doc, path: Path) -> None:
    """Render a Doc to DOCX with real heading styles so the parser can detect sections."""
    document = DocxDocument()
    document.styles["Normal"].font.size = Pt(10.5)
    document.add_heading(doc.title, level=0)
    document.add_paragraph(doc.subtitle)
    document.add_paragraph(COMPANY)
    for kind, payload in doc.blocks:
        if kind == "h1":
            document.add_heading(str(payload), level=1)
        elif kind == "h2":
            document.add_heading(str(payload), level=2)
        elif kind == "p":
            document.add_paragraph(str(payload))
        elif kind == "bullets":
            for item in payload:  # type: ignore[union-attr]
                document.add_paragraph(item, style="List Bullet")
        elif kind == "table":
            rows = payload  # type: ignore[assignment]
            table = document.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Table Grid"
            for r, row in enumerate(rows):
                for c, text in enumerate(row):
                    cell = table.cell(r, c)
                    cell.text = text
                    if r == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
            document.add_paragraph()
        elif kind == "pagebreak":
            document.add_page_break()
    document.save(str(path))


def render_txt(doc: Doc, path: Path) -> None:
    """Render a Doc to plain text with Markdown-like headings and pipe tables."""
    lines = [doc.title.upper(), doc.subtitle, COMPANY, ""]
    for kind, payload in doc.blocks:
        if kind == "h1":
            lines += ["", f"# {payload}", ""]
        elif kind == "h2":
            lines += ["", f"## {payload}", ""]
        elif kind == "p":
            lines += [str(payload), ""]
        elif kind == "bullets":
            lines += [f"- {item}" for item in payload] + [""]  # type: ignore[union-attr]
        elif kind == "table":
            rows = payload  # type: ignore[assignment]
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("|" + "|".join("---" for _ in rows[0]) + "|")
            lines += ["| " + " | ".join(r) + " |" for r in rows[1:]] + [""]
        elif kind == "pagebreak":
            lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


RENDERERS = {".pdf": render_pdf, ".docx": render_docx, ".txt": render_txt}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "sample_docs",
        help="output directory (default: data/sample_docs)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args.out.mkdir(parents=True, exist_ok=True)
    for build in ALL_DOCS:
        doc = build()
        path = args.out / doc.filename
        RENDERERS[path.suffix](doc, path)
        logger.info(
            "wrote %s (%s, %d blocks, %d bytes)",
            path.name,
            doc.language,
            len(doc.blocks),
            path.stat().st_size,
        )
    logger.info("done: %d documents in %s", len(ALL_DOCS), args.out)


if __name__ == "__main__":
    main()
