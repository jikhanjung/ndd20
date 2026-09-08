from django import forms
from .models import CropReview


class JudgmentForm(forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)

    class Meta:
        model = CropReview
        fields = ["decision", "image_quality", "mask_quality", "base_quality", "reviewer", "notes"]
        labels = {"decision": "최종 판정", "image_quality": "원영상", "mask_quality": "모델 마스크",
                  "base_quality": "모델 밑동", "reviewer": "판정자", "notes": "판정 근거 / 수정할 내용"}
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["decision"].label = "최종 판정"
        self.fields["reviewer"].required = True
