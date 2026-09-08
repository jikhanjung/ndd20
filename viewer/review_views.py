import io
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from PIL import Image

from ndd import crop, labels
from .forms import JudgmentForm
from .models import CropReview, ReviewHistory, Run
from .views import _card


def selection(request):
    qs = CropReview.objects.select_related("run")
    run = request.GET.get("run", "")
    if run.isdigit():
        qs = qs.filter(run_id=int(run))
    else:
        latest = Run.objects.order_by("-pk").first()
        qs = qs.filter(run=latest)
    state = request.GET.get("state", "")
    if state in dict(CropReview.DECISIONS):
        qs = qs.filter(decision=state)
    scope = request.GET.get("scope", "id")
    if scope == "id":
        qs = qs.exclude(individual="")
    if request.GET.get("ind"):
        qs = qs.filter(individual=request.GET["ind"])
    if request.GET.get("ai") == "reviewed":
        qs = qs.exclude(ai_review={})
    elif request.GET.get("ai") == "pending":
        qs = qs.filter(ai_review={})
    return qs


def card(obj):
    c = _card(obj.key, labels.Region(**obj.label), obj.prediction)
    c["image_url"] = f"/review/{obj.pk}/image"
    return c


@require_GET
def queue(request):
    from django.core.paginator import Paginator
    qs = selection(request)
    page = Paginator(qs, 36).get_page(request.GET.get("page"))
    entries = [{"obj": obj, "c": card(obj)} for obj in page]
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "viewer/review_queue.html", {
        "entries": entries, "page": page, "query": params.urlencode(),
        "runs": Run.objects.order_by("-pk"), "decisions": CropReview.DECISIONS,
        "total": qs.count(), "pending": qs.filter(decision="pending").count(),
        "ai_count": qs.exclude(ai_review={}).count(),
        "active_run": str(qs.first().run_id) if qs.exists() else request.GET.get("run", ""),
        "filters": request.GET, "scope": request.GET.get("scope", "id"),
    })


@require_http_methods(["GET", "POST"])
def detail(request, pk):
    obj = get_object_or_404(CropReview.objects.select_related("run"), pk=pk)
    form = JudgmentForm(request.POST or None, instance=obj, initial={"version": obj.version})
    conflict = False
    if request.method == "POST" and form.is_valid():
        fields = JudgmentForm.Meta.fields
        values = {k: form.cleaned_data[k] for k in fields}
        version = form.cleaned_data["version"]
        from django.utils import timezone
        with transaction.atomic():
            changed = CropReview.objects.filter(pk=pk, version=version).update(
                **values, version=version + 1, updated_at=timezone.now())
            if changed:
                ReviewHistory.objects.create(crop_id=pk, version=version + 1, judgment=values)
            else:
                conflict = True
                form.add_error(None, "다른 화면에서 판정이 갱신됐습니다. 새로고침 후 최신 판정을 확인하고 다시 저장하세요.")
        if changed:
            target = pk
            if request.POST.get("action") == "next":
                following = selection(request).filter(pk__gt=pk).first()
                if following:
                    target = following.pk
            return redirect(f"/review/{target}?{request.GET.urlencode()}")
    # ModelForm mutates its instance during validation; fetch persisted data for the panels.
    obj.refresh_from_db()
    neighbors = selection(request)
    return render(request, "viewer/review_detail.html", {
        "obj": obj, "c": card(obj), "form": form, "query": request.GET.urlencode(),
        "previous": neighbors.filter(pk__lt=pk).order_by("-pk").first(),
        "following": neighbors.filter(pk__gt=pk).first(),
        "history": obj.history.all()[:20], "conflict": conflict,
    }, status=409 if conflict else 200)


@require_GET
def review_image(request, pk):
    obj = get_object_or_404(CropReview, pk=pk)
    root = Path(settings.NDD20_DIR).resolve()
    src = (root / obj.kind / obj.image).resolve()
    if not src.is_relative_to(root) or not src.is_file():
        raise Http404("원본 이미지를 찾을 수 없습니다. NDD20_DIR를 확인하세요.")
    with Image.open(src) as im:
        if request.GET.get("full") != "1":
            im = im.crop(crop.view_box(labels.Region(**obj.label)))
        im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=92)
    buf.seek(0)
    return FileResponse(buf, content_type="image/jpeg")
