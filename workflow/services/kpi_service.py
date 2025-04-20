from datetime import date, timedelta

import calendar

from decimal import Decimal

from typing import Dict, Any, Tuple

from django.db.models import Sum, Q
from logging import getLogger

from workflow.models import TimeEntry, CompanyDefaults, Job
from workflow.utils import get_excluded_staff

logger = getLogger(__name__)


class KPIService:
    """
    Service responsible for calculating and providing KPI metrics for reports.
    All business logic related to KPIs shall be implemented here.
    """

    @staticmethod
    def get_company_thresholds() -> Dict[str, float]:
        """
        Gets KPI thresholds based on CompanyDefaults

        Returns:
            Dict containing thresholds for KPI metrics
        """
        logger.info("Retrieving company thresholds for KPI calculations")
        try:
            company_defaults = CompanyDefaults.objects.first()
            thresholds = {
                "billable_threshold_green": float(company_defaults.billable_threshold_green),
                "billable_threshold_amber": float(company_defaults.billable_threshold_amber),
                "daily_gp_target": float(company_defaults.daily_gp_target),
                "shop_hours_target": float(company_defaults.shop_hours_target_percentage)
            }
            logger.debug(f"Retrieved thresholds: {thresholds}")
            return thresholds
        except Exception as e:
            logger.error(f"Error retrieving company defaults: {str(e)}")
            logger.warning("Using fallback threshold values")
            return {
                "billable_threshold_green": 45,
                "billable_threshold_amber": 30,
                "daily_gp_target": 2500,
                "shop_hours_target": 20
            }
    
    @classmethod
    def get_month_days_range(cls, year: int, month: int) -> Tuple[date, date, int]:
        """
        Gets the daily range for a specific month.

        Args:
            year: calendar year
            month: calendar month (1-12)
        
        Returns:
            Tuple containing initial date, final date and number of days of the month
        """
        logger.info(f"Calculating date range for year={year}, month={month}")
        _, num_days = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)
        
        logger.debug(f"Date range: {start_date} to {end_date}, days in month: {num_days}")
        return start_date, end_date, num_days
    
    @classmethod
    def get_calendar_data(cls, year: int, month: int) -> Dict[str, Any]:
        """
        Gets all KPI data for a specific month.

        Args:
            year: calendar year
            month: calendar month (1-12)

        Returns:
            Dict containing calendar data, monthly totals and threshold informations
        """
        logger.info(f"Generating KPI calendar data for {year}-{month}")
        
        thresholds = cls.get_company_thresholds()
        logger.debug(f"Using thresholds: green={thresholds['billable_threshold_green']}, amber={thresholds['billable_threshold_amber']}")

        start_date, end_date, _ = cls.get_month_days_range(year, month)
        excluded_staff_ids = get_excluded_staff()
        logger.debug(f"Excluded staff IDs: {excluded_staff_ids}")

        calendar_data = {}
        monthly_totals = {
            "billable_hours": 0,
            "total_hours": 0,
            "shop_hours": 0,
            "gross_profit": 0,
            "days_green": 0,
            "days_amber": 0,
            "days_red": 0,
            "working_days": 0
        }

        # For each day of the month
        current_date = start_date
        while current_date <= end_date:
            # For some reason week days in Python are 0 based, so 5 is Saturday and 6 is Sunday
            if current_date.weekday() >= 5: 
                current_date += timedelta(days=1)
                continue

            # Count commercial day
            monthly_totals["working_days"] += 1
            logger.debug(f"Processing data for day: {current_date}")

            # Process data of the day
            day_data = cls._process_day_data(
                current_date,
                excluded_staff_ids,
                thresholds["billable_threshold_green"],
                thresholds["billable_threshold_amber"],
                thresholds["daily_gp_target"]
            )

            # Add data to dict
            calendar_data[current_date.isoformat()] = day_data
            logger.debug(f"Day {current_date} status: {day_data['color']}, billable hours: {day_data['billable_hours']}")

            # Update monthly totals
            monthly_totals["billable_hours"] += day_data["billable_hours"]
            monthly_totals["total_hours"] += day_data["total_hours"]
            monthly_totals["shop_hours"] += day_data["shop_hours"]
            monthly_totals["gross_profit"] += day_data["gross_profit"]

            # Increment status counters
            if day_data["color"] == "green":
                monthly_totals["days_green"] += 1
            elif day_data["color"] == "amber":
                monthly_totals["days_amber"] += 1
            elif day_data["color"] == "red":
                monthly_totals["days_red"] += 1
            else:
                logger.error(f"Unknown color status for day {current_date}: {day_data['color']}")
                raise ValueError(f"Unknown color for day data: {day_data['color']}")

            # Advance to next day
            current_date += timedelta(days=1)
        
        # Calculate percentages after all days processed
        cls._calculate_monthly_percentages(monthly_totals)
        logger.info(f"Monthly totals: billable: {monthly_totals['billable_hours']:.1f}h, billable %: {monthly_totals['billable_percentage']:.1f}%")
        logger.info(f"Performance: green days: {monthly_totals['days_green']}, amber: {monthly_totals['days_amber']}, red: {monthly_totals['days_red']}")

        response_data = {
            "calendar_data": calendar_data,
            "monthly_totals": monthly_totals,
            "thresholds": thresholds,
            "year": year,
            "month": month
        }
        logger.debug(f"Calendar data generated with {len(calendar_data)} days")
        return response_data
    
    @staticmethod
    def _process_day_data(
        day_date: date,
        excluded_staff_ids: list,
        threshold_green: float,
        threshold_amber: float,
        gp_target: float
    ) -> Dict[str, Any]:
        """
        Process data of a specific day for the KPI Calendar

        Args:
            day_date: data of the day to be processed
            excluded_staff_ids: IDs list of excluded staff
            threshold_green: threshold for green status
            threshold_amber: threshold for amber status
            gp_target: gross profit daily target
        
        Returns:
            Dict containing processed data of the day
        """
        try:
            logger.debug(f"Processing day data for {day_date}")
            
            # Consult time entries for the day
            day_entries: list[TimeEntry] = TimeEntry.objects.filter(
                date=day_date
            ).exclude(
                staff_id__in=excluded_staff_ids
            ).select_related("job_pricing", "job_pricing__job")
            
            logger.debug(f"Found {len(day_entries)} time entries for {day_date}")

            # Calc hours
            billable_hours = Decimal("0.0")
            total_hours = Decimal("0.0")
            shop_hours = Decimal("0.0")
            billable_revenue = Decimal("0.0")
            staff_wage_cost = Decimal("0.0")
            gross_profit = Decimal("0.0")

            for entry in day_entries:
                total_hours += entry.hours
                
                if entry.is_billable:
                    billable_hours += entry.hours
                    billable_revenue += entry.hours * entry.charge_out_rate
                    
                staff_wage_cost += entry.hours * entry.wage_rate
                gross_profit += billable_revenue - staff_wage_cost

                # Verificar de forma segura se é um job de shop
                is_shop_job = False
                try:
                    # Tente usar a propriedade shop_job se disponível
                    is_shop_job = entry.job_pricing.job.shop_job
                except (AttributeError, Exception):
                    # Se não funcionar, verifique pelo client_id
                    try:
                        is_shop_job = (str(entry.job_pricing.job.client_id) == "00000000-0000-0000-0000-000000000001")
                    except (AttributeError, Exception):
                        logger.warning(f"Could not determine if job is shop job for entry ID: {entry.id}")
                        pass
                
                if is_shop_job:
                    shop_hours += entry.hours

            # Calc shop hours percentage
            shop_percentage = (Decimal(shop_hours) / Decimal(total_hours) * 100) if total_hours > 0 else Decimal("0")
            
            # Log the calculations
            logger.debug(f"Day {day_date} - Total: {total_hours}h, Billable: {billable_hours}h, Shop: {shop_hours}h ({shop_percentage:.1f}%), GP: ${gross_profit}")

            # Determine color based on threshold
            if billable_hours >= threshold_green:
                color = "green"
            elif billable_hours >= threshold_amber:
                color = "amber"
            else:
                color = "red"
            
            logger.debug(f"Day {day_date} status: {color} (thresholds: green>={threshold_green}, amber>={threshold_amber})")
            
            return {
                "date": day_date.isoformat(),
                "day": day_date.day,
                "billable_hours": float(billable_hours),
                "total_hours": float(total_hours),
                "shop_hours": float(shop_hours),
                "shop_percentage": float(shop_percentage),
                "gross_profit": float(gross_profit),
                "color": color,
                "gp_target_achievement": float(Decimal(gross_profit) / Decimal(gp_target) * 100) if gp_target > 0 else 0
            }
        except Exception as e:
            import traceback
            logger.error(f"Error processing data for day {day_date}: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "date": day_date.isoformat(),
                "day": day_date.day,
                "billable_hours": 0.0,
                "total_hours": 0.0,
                "shop_hours": 0.0,
                "shop_percentage": 0.0,
                "gross_profit": 0.0,
                "color": "red",
                "gp_target_achievement": 0.0,
            }
        
    @staticmethod
    def _calculate_monthly_percentages(monthly_totals: Dict[str, float]) -> None:
        """
        Calculate percentages and medias for monthly totals

        Args:
            monthly_totals: Dict of monthly totals to be updated
        """
        logger.debug("Calculating monthly percentages")
        
        # Initialize default values
        monthly_totals["billable_percentage"] = 0
        monthly_totals["shop_percentage"] = 0
        monthly_totals["avg_daily_gp"] = 0

        # Calculate billable and shop percentages if we have hours
        if monthly_totals["total_hours"] > 0:
            monthly_totals["billable_percentage"] = round(
                Decimal(monthly_totals["billable_hours"]) / Decimal(monthly_totals["total_hours"])  * 100, 1
            )
            monthly_totals["shop_percentage"] = round(
                Decimal(monthly_totals["shop_hours"] / monthly_totals["total_hours"]) * 100, 1
            )
            logger.debug(f"Calculated billable percentage: {monthly_totals['billable_percentage']}%, shop percentage: {monthly_totals['shop_percentage']}%")

        # Calculate average daily gross profit if we have working days
        if monthly_totals["working_days"] > 0:
            monthly_totals["avg_daily_gp"] = round(
                Decimal(monthly_totals["gross_profit"] / monthly_totals["working_days"]), 2
            )
            logger.debug(f"Calculated average daily gross profit: ${monthly_totals['avg_daily_gp']}")
        else:
            logger.warning("No working days found for month - average GP will be zero")
