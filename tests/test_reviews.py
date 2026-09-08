import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import Client, TestCase

from ndd.labels import Region
from viewer.models import CropReview, ReviewHistory, Run


class ReviewTests(TestCase):
    def setUp(self):
        self.run = Run.objects.create(name="test", source="test.jsonl", sha256="a" * 64)
        self.obj = CropReview.objects.create(run=self.run, kind="ABOVE", key="1.jpg~0",
            image="1.jpg", individual="13", label=asdict(Region(
                image="1.jpg", kind="ABOVE", shape="polyline", xs=[0, 20, 0], ys=[0, 20, 20], ind="13")),
            prediction={"key": "1.jpg~0", "mask": None})
        self.url = f"/review/{self.obj.pk}"
        self.values = dict(decision="accept", image_quality="good", mask_quality="missing",
                           base_quality="missing", reviewer="검토자", notes="이미지는 사용 가능", version=0)

    def test_save_history_and_reject_stale_write(self):
        self.assertEqual(self.client.post(self.url, self.values).status_code, 302)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.decision, "accept")
        self.assertEqual(self.obj.version, 1)
        self.assertEqual(self.obj.history.get().judgment["notes"], "이미지는 사용 가능")
        self.assertEqual(self.client.post(self.url, {**self.values, "decision": "exclude"}).status_code, 409)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.decision, "accept")
        self.assertEqual(ReviewHistory.objects.count(), 1)

    def test_validation(self):
        for change in [{"reviewer": ""}, {"decision": "arbitrary"}, {"version": ""}]:
            response = self.client.post(self.url, {**self.values, **change})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(ReviewHistory.objects.exists())

    def test_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, self.values).status_code, 403)
        client.get(self.url)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.url, {**self.values, "csrfmiddlewaretoken": token}).status_code, 302)

    def test_queue_filters_and_pending_ai(self):
        response = self.client.get("/")
        self.assertContains(response, "AI 미검토")
        self.assertEqual(response.context["total"], 1)
        self.assertEqual(self.client.get("/?ai=reviewed").context["total"], 0)
        self.client.post(self.url, self.values)
        self.assertEqual(self.client.get("/?state=pending").context["total"], 0)
        self.assertEqual(self.client.get("/?state=accept").context["total"], 1)

    def test_save_next_keeps_filter(self):
        next_obj = CropReview.objects.create(run=self.run, kind="ABOVE", key="2.jpg~0",
            image="2.jpg", individual="13", label=self.obj.label, prediction={"mask": None})
        response = self.client.post(self.url + "?state=pending", {**self.values, "action": "next"})
        self.assertEqual(response.url, f"/review/{next_obj.pk}?state=pending")

    def test_import_is_idempotent_and_preserves_judgment(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            label = {"one": {"filename": "1.jpg", "regions": [{"shape_attributes": {
                "name": "polyline", "all_points_x": [0, 20, 0], "all_points_y": [0, 20, 20]},
                "region_attributes": {"id": "13"}}]}}
            # Test fixtures only; no project or source data is modified.
            (root / "ABOVE_LABELS.json").write_text(json.dumps(label))
            path = root / "test.jsonl"
            path.write_text(json.dumps({"key": "1.jpg~0", "mask": None}) + "\n")
            call_command("import_reviews", str(path), dir=temp, verbosity=0)
            obj = CropReview.objects.exclude(run=self.run).get()
            self.client.post(f"/review/{obj.pk}", self.values)
            call_command("import_reviews", str(path), dir=temp, verbosity=0)
            obj.refresh_from_db()
            self.assertEqual(obj.decision, "accept")
            self.assertEqual(obj.history.count(), 1)
            self.assertEqual(CropReview.objects.exclude(run=self.run).count(), 1)
