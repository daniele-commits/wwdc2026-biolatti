# -*- coding: utf-8 -*-
"""Test offline di update_news.py e accenti.py (nessuna rete: l'API è mockata).
Esecuzione:  python3 -m unittest discover -s tests -v
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import accenti  # noqa: E402
import update_news as un  # noqa: E402


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_item(slug="ios-27-nuova-funzione-test", title_it="iOS 27 introduce una funzione di prova",
              title_en="iOS 27 introduces a test feature", official=True, **kw):
    src = [{"title": "MacRumors", "url": "https://www.macrumors.com/2026/06/09/x/"}]
    if official:
        src.append({"title": "Apple Newsroom", "url": "https://www.apple.com/newsroom/2026/06/x/"})
    it = {
        "slug": slug, "macroArea": "sistemi-operativi", "tags": ["design"],
        "category": "Sistemi operativi", "titleIt": title_it, "titleEn": title_en,
        "excerptIt": "Una sintesi.", "excerptEn": "A summary.",
        "bodyIt": "Testo.", "bodyEn": "Text.", "sources": src,
    }
    it.update(kw)
    return it


def api_response(items, stop_reason="end_turn", raw=None):
    text = raw if raw is not None else "Ricerca fatta.\n```json\n" + json.dumps({"newItems": items}) + "\n```"
    return {"content": [{"type": "text", "text": text}], "stop_reason": stop_reason, "usage": {}}


class TestAccenti(unittest.TestCase):
    def test_regole_base(self):
        f = accenti.fix_accents
        self.assertEqual(f("il modello piú potente é esclusivo"), "il modello più potente è esclusivo")
        self.assertEqual(f("E' vero che e' piu' veloce"), "È vero che è più veloce")
        self.assertEqual(f("Perche conta: gia oggi puo"), "Perché conta: già oggi può")
        self.assertEqual(f("la novita' e la qualitá, c'e anche"), "la novità e la qualità, c'è anche")
        self.assertEqual(f("sull'eta e sara' disponibile"), "sull'età e sarà disponibile")

    def test_acute_corrette_restano(self):
        s = "perché né sé anziché finché cosicché poiché"
        self.assertEqual(accenti.fix_accents(s), s)

    def test_ambigue_e_nomi_non_toccati(self):
        s = "Sara usa Meta, facilita l'unita; il CIO e Guaraní"
        self.assertEqual(accenti.fix_accents(s), s)

    def test_url_slug_codice_protetti(self):
        s = "vedi `slug-con-piu-parole` e [piu info](https://x.com/perche-piu) e on-device-piu-potente"
        out = accenti.fix_accents(s)
        self.assertIn("`slug-con-piu-parole`", out)
        self.assertIn("(https://x.com/perche-piu)", out)
        self.assertIn("on-device-piu-potente", out)
        self.assertIn("[più info]", out)

    def test_campi_en_non_toccati(self):
        it = make_item(titleIt="Il piú veloce", titleEn="The fastest é piu")
        accenti.fix_item_it_fields(it)
        self.assertEqual(it["titleIt"], "Il più veloce")
        self.assertEqual(it["titleEn"], "The fastest é piu")
        self.assertEqual(it["slug"], "ios-27-nuova-funzione-test")


class TestParse(unittest.TestCase):
    def test_valido_e_vuoto(self):
        self.assertEqual(len(un.parse_new_items(api_response([make_item()])["content"][0]["text"])), 1)
        self.assertEqual(un.parse_new_items('```json\n{"newItems": []}\n```'), [])

    def test_errori(self):
        for bad in ["nessun json qui", '```json\n{"newItems": [ {"a": 1,\n```', '```json\n{"altro": 1}\n```']:
            with self.assertRaises(un.ParseError):
                un.parse_new_items(bad)


class TestValidate(unittest.TestCase):
    def test_ok_con_fonte_ufficiale_e_accenti(self):
        it = make_item(bodyIt="E' il piú atteso")
        v, st, _ = un.validate(it, set(), [])
        self.assertEqual(st, "ok")
        self.assertEqual(v["bodyIt"], "È il più atteso")
        self.assertTrue(un.is_official(v["sources"][0]["url"]))  # ufficiale in testa

    def test_slug_duplicato(self):
        _, st, why = un.validate(make_item(), {"ios-27-nuova-funzione-test"}, [])
        self.assertEqual(st, "reject")
        self.assertIn("slug", why)

    def test_titolo_simile(self):
        existing = ["iOS 27 introduce una funzione di prova!"]
        _, st, why = un.validate(make_item(slug="altro-slug-diverso-qui"), set(), existing)
        self.assertEqual(st, "reject")
        self.assertIn("simile", why)

    def test_titolo_diverso_passa(self):
        _, st, _ = un.validate(make_item(), set(), ["watchOS 27 porta nuovi quadranti"])
        self.assertEqual(st, "ok")

    def test_senza_fonte_ufficiale_va_in_revisione(self):
        v, st, _ = un.validate(make_item(official=False), set(), [])
        self.assertEqual(st, "review")
        self.assertEqual(v["status"], "da verificare")

    def test_domini_non_ammessi_scartati(self):
        it = make_item(official=False, sources=[{"title": "x", "url": "https://blog-a-caso.example/p"}])
        _, st, _ = un.validate(it, set(), [])
        self.assertEqual(st, "reject")

    def test_sottodominio_apple_ufficiale(self):
        self.assertTrue(un.is_official("https://developer.apple.com/news/"))
        self.assertFalse(un.is_official("https://apple.com.evil.example/"))


class TestPrompt(unittest.TestCase):
    def test_solo_ultimi_40_titoli(self):
        data = {"items": [{"slug": f"slug-numero-{i}", "titleIt": f"Titolo {i}"} for i in range(100)]}
        p = un.build_prompt(un.recent_titles(data))
        self.assertIn("Titolo 0", p)
        self.assertIn("Titolo 39", p)
        self.assertNotIn("Titolo 40", p)
        self.assertNotIn("slug-numero-", p)


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data_file = os.path.join(self.tmp, "news.json")
        self.review = os.path.join(self.tmp, "review_queue.json")
        self.notify = os.path.join(self.tmp, "notify.json")
        end = (datetime.now(un.TZ) + timedelta(days=1)).isoformat()
        self.data = {"eventEnd": end, "items": [make_item(slug="esistente-slug-uno", title_it="Vecchio annuncio su Siri",
                                                          title_en="Old Siri announcement")]}
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f)
        self.patches = [
            mock.patch.object(un, "DATA_FILE", self.data_file),
            mock.patch.object(un, "REVIEW_FILE", self.review),
            mock.patch.object(un, "NOTIFY_FILE", self.notify),
            mock.patch.object(un.subprocess, "run",
                              return_value=mock.Mock(returncode=0, stdout="build ok\n", stderr="")),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        ]
        for p in self.patches:
            p.start()
        os.environ.pop("WWDC_FORCE", None)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.tmp)

    def run_main(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            un.main()
        return buf.getvalue()

    def test_finestra_chiusa_prima_della_chiave(self):
        self.data["eventEnd"] = "2026-06-12T23:59:00+02:00"
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}), \
                mock.patch.object(un, "call_anthropic") as api:
            out = self.run_main()  # nessun SystemExit anche senza chiave
        api.assert_not_called()
        self.assertIn("SUMMARY::0::finestra chiusa", out)

    def test_chiave_mancante_in_finestra_errore(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}), \
                mock.patch.object(un, "call_anthropic") as api, self.assertRaises(SystemExit) as cm:
            self.run_main()
        self.assertEqual(cm.exception.code, 1)
        api.assert_not_called()

    def test_max_tokens_job_rosso(self):
        with mock.patch.object(un, "call_anthropic", return_value=api_response([make_item()], "max_tokens")), \
                self.assertRaises(SystemExit) as cm:
            self.run_main()
        self.assertEqual(cm.exception.code, 1)

    def test_risposta_non_interpretabile_job_rosso(self):
        with mock.patch.object(un, "call_anthropic", return_value=api_response(None, raw="Non ho trovato nulla.")), \
                self.assertRaises(SystemExit) as cm:
            self.run_main()
        self.assertEqual(cm.exception.code, 1)

    def test_lista_vuota_successo(self):
        with mock.patch.object(un, "call_anthropic", return_value=api_response([])):
            out = self.run_main()
        self.assertIn("SUMMARY::0::nessuna novita", out)

    def test_flusso_completo_pubblica_e_accoda(self):
        ok = make_item(slug="ios-27-funzione-ufficiale", title_it="iOS 27: arriva la funzione piú attesa",
                       title_en="iOS 27: the most awaited feature arrives")
        rev = make_item(slug="macos-27-rumor-senza-fonte", title_it="macOS 27 cambia il Finder",
                        title_en="macOS 27 changes the Finder", official=False)
        dup = make_item(slug="slug-nuovo-ma-titolo-vecchio", title_it="Vecchio annuncio su Siri.",
                        title_en="Old Siri announcement.")
        with mock.patch.object(un, "call_anthropic", return_value=api_response([ok, rev, dup])):
            out = self.run_main()
        self.assertIn("SUMMARY::1::iOS 27: arriva la funzione più attesa", out)
        data = _load(self.data_file)
        slugs = [i["slug"] for i in data["items"]]
        self.assertEqual(slugs, ["ios-27-funzione-ufficiale", "esistente-slug-uno"])
        queue = _load(self.review)
        self.assertEqual([q["slug"] for q in queue], ["macos-27-rumor-senza-fonte"])
        self.assertEqual(queue[0]["status"], "da verificare")
        notify = _load(self.notify)
        self.assertEqual(len(notify), 1)

    def test_coda_revisione_si_accumula(self):
        un.queue_for_review([{"slug": "a"}], self.review)
        un.queue_for_review([{"slug": "b"}], self.review)
        self.assertEqual([q["slug"] for q in _load(self.review)], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
