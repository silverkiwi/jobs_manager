from typing import Any, Dict, List, Optional, Type

from django.db.models import QuerySet
from django.views.generic import DetailView

from workflow.models import (
    AdjustmentEntry,
    Job,
    JobPricing,
    MaterialEntry,
    TimeEntry,
)

HistoricalJob = Job.history.model


class JobDetailView(DetailView):
    model: Type[Job] = Job
    template_name: str = "workflow/job_detail.html"
    context_object_name: str = "job"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        job: Job = self.object

        pricing_models: QuerySet[JobPricing] = job.pricings.all()
        pricing_data: List[Dict[str, Any]] = []

        for model in pricing_models:
            time_entries: QuerySet[TimeEntry] = model.time_entries.all()
            material_entries: QuerySet[MaterialEntry] = model.material_entries.all()
            adjustment_entries: QuerySet[AdjustmentEntry] = model.adjustment_entries.all()

            total_time_cost: float = sum(entry.cost for entry in time_entries)
            total_time_revenue: float = sum(entry.revenue for entry in time_entries)

            total_material_cost: float = sum(entry.cost for entry in material_entries)
            total_material_revenue: float = sum(entry.revenue for entry in material_entries)

            total_adjustment_cost: float = sum(entry.cost for entry in adjustment_entries)
            total_adjustment_revenue: float = sum(entry.revenue for entry in adjustment_entries)

            total_cost: float = (
                total_time_cost + total_material_cost + total_adjustment_cost
            )
            total_revenue: float = (
                total_time_revenue + total_material_revenue + total_adjustment_revenue
            )

            pricing_data.append(
                {
                    "model": model,
                    "total_time_cost": total_time_cost,
                    "total_time_revenue": total_time_revenue,
                    "total_material_cost": total_material_cost,
                    "total_material_revenue": total_material_revenue,
                    "total_adjustment_cost": total_adjustment_cost,
                    "total_adjustment_revenue": total_adjustment_revenue,
                    "total_cost": total_cost,
                    "total_revenue": total_revenue,
                }
            )

        context["pricing_data"] = pricing_data

        history: QuerySet[HistoricalJob] = job.history.all()
        history_diffs: List[Dict[str, Any]] = []
        history_length: int = history.count()

        for i in range(history_length - 1):
            new_record = history[i]
            old_record = history[i + 1]
            delta = new_record.diff_against(old_record)
            changes = [
                {"field": change.field, "old": change.old, "new": change.new}
                for change in delta.changes
            ]
            history_diffs.append(
                {
                    "record": new_record,
                    "changes": changes,
                    "changed_by": new_record.history_user_id,
                }
            )

        # Add the initial record with no changes
        if history.exists():
            initial_record: Optional[HistoricalJob] = history.last()
            if initial_record:
                history_diffs.append(
                    {
                        "record": initial_record,
                        "changes": [],
                        "changed_by": initial_record.history_user_id,
                    }
                )

        context["history_diffs"] = history_diffs

        return context
