"""Import immutable label/inference snapshots, without overwriting judgments."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from ndd import labels
from viewer.models import CropReview, Run


class Command(BaseCommand):
    help = "라벨과 추론 JSONL을 검토 DB에 가져옵니다. 기존 판정은 보존합니다."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--set", choices=labels.SETS, default="ABOVE")
        parser.add_argument("--dir")
        parser.add_argument("--ai", help="실제로 수행한 AI 검토 JSON 목록")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = Path(opts["path"]).resolve()
        data = path.read_bytes()
        rows = [json.loads(line) for line in data.splitlines() if line.strip()]
        if len({r["key"] for r in rows}) != len(rows):
            raise CommandError("추론 결과에 중복 key가 있습니다.")
        keyed, seen = {}, {}
        for r in labels.load(opts["set"], opts["dir"]):
            i = seen.get(r.image, 0)
            seen[r.image] = i + 1
            keyed[f"{r.image}~{i}"] = asdict(r)
        # Include label content and set: same predictions against changed labels are a new run.
        digest = hashlib.sha256(data + json.dumps(keyed, sort_keys=True).encode()).hexdigest()
        run, _ = Run.objects.get_or_create(sha256=digest, defaults={
            "name": f"{path.parent.name}/{path.stem}", "source": str(path)})
        ai = {}
        if opts["ai"]:
            ai = {r["key"]: r for r in json.loads(Path(opts["ai"]).read_text())}
        created = 0
        for row in rows:
            if row["key"] not in keyed:
                raise CommandError(f"라벨에 없는 key: {row['key']}")
            label = keyed[row["key"]]
            obj, new = CropReview.objects.get_or_create(run=run, kind=opts["set"], key=row["key"], defaults={
                "image": label["image"], "individual": label["ind"], "label": label,
                "prediction": row, "ai_review": ai.get(row["key"], {})})
            if not new and not obj.ai_review and row["key"] in ai:
                obj.ai_review = ai[row["key"]]
                obj.save(update_fields=["ai_review"])
            created += new
        self.stdout.write(self.style.SUCCESS(f"판 {run.pk}: {len(rows)}개 중 신규 {created}개. 기존 판정 보존."))
