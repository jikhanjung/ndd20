from django.db import models


class Run(models.Model):
    name = models.CharField(max_length=200)
    source = models.TextField()
    sha256 = models.CharField(max_length=64, unique=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CropReview(models.Model):
    DECISIONS = [("pending", "미판정"), ("accept", "사용 가능"),
                 ("repair", "수정 필요"), ("exclude", "사용 제외"), ("hold", "보류")]
    QUALITY = [("unknown", "미확인"), ("good", "적절함"),
               ("bad", "문제 있음"), ("missing", "없음"), ("uncertain", "불확실")]
    run = models.ForeignKey(Run, on_delete=models.PROTECT)
    kind = models.CharField(max_length=10)
    key = models.CharField(max_length=200)
    image = models.CharField(max_length=200)
    individual = models.CharField(max_length=100, blank=True)
    # Import snapshots retain original coordinates and every inference field.
    label = models.JSONField()
    prediction = models.JSONField()
    ai_review = models.JSONField(default=dict, blank=True)
    decision = models.CharField(max_length=20, choices=DECISIONS, default="pending")
    image_quality = models.CharField(max_length=20, choices=QUALITY, default="unknown")
    mask_quality = models.CharField(max_length=20, choices=QUALITY, default="unknown")
    base_quality = models.CharField(max_length=20, choices=QUALITY, default="unknown")
    reviewer = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "kind", "key"], name="unique_run_crop")]
        ordering = ["pk"]


class ReviewHistory(models.Model):
    crop = models.ForeignKey(CropReview, on_delete=models.PROTECT, related_name="history")
    version = models.PositiveIntegerField()
    judgment = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["crop", "version"], name="unique_review_version")]
