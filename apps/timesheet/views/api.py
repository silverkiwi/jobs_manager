"""
REST API views for timesheet functionality.
Provides endpoints for the Vue.js frontend to interact with timesheet data.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from django.db.models import Q, Sum, Prefetch
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models import Job, JobPricing
from apps.timesheet.models import TimeEntry
from apps.timesheet.serializers import (
    TimeEntryAPISerializer,
    StaffAPISerializer, 
    JobPricingAPISerializer
)
from apps.timesheet.enums import RateType

logger = logging.getLogger(__name__)


class StaffListAPIView(APIView):
    """API endpoint to get list of staff members for timesheet."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get filtered list of staff members."""
        try:
            excluded_staff_ids = get_excluded_staff()
            staff = Staff.objects.exclude(
                Q(is_staff=True) | Q(id__in=excluded_staff_ids)
            ).order_by('last_name', 'first_name')
            
            staff_data = []
            for member in staff:
                staff_data.append({
                    'id': str(member.id),
                    'name': member.get_display_name() or 'Unknown',
                    'firstName': member.first_name or '',
                    'lastName': member.last_name or '',
                    'email': member.email or '',
                    'avatarUrl': None  # Add avatar logic if needed
                })
            
            return Response({'staff': staff_data})
        
        except Exception as e:
            logger.error(f"Error fetching staff list: {e}")
            return Response(
                {'error': 'Failed to fetch staff list', 'details': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TimeEntriesAPIView(APIView):
    """API endpoint for timesheet entries CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get time entries for a specific staff member and date range."""
        staff_id = request.query_params.get('staff_id')
        date = request.query_params.get('date')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not staff_id:
            return Response({'error': 'staff_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff member not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Build query filters
        filters = Q(staff=staff)
        
        if date:
            parsed_date = parse_date(date)
            if parsed_date:
                filters &= Q(date=parsed_date)
        elif start_date and end_date:
            parsed_start = parse_date(start_date)
            parsed_end = parse_date(end_date)
            if parsed_start and parsed_end:
                filters &= Q(date__range=[parsed_start, parsed_end])
          # Get time entries with related data
        time_entries = TimeEntry.objects.filter(filters).select_related(
            'staff', 'job_pricing__job'
        ).order_by('date', 'created_at')
        
        # Serialize data
        serializer = TimeEntryAPISerializer(time_entries, many=True)
        
        return Response({'time_entries': serializer.data})
    def post(self, request):
        """Create a new time entry."""
        data = request.data
        
        try:
            staff_id = data.get('staff_id') or data.get('staffId')  # Handle both formats
            job_pricing_id = data.get('job_pricing_id') or data.get('jobPricingId')  # Handle both formats
            
            if not staff_id:
                return Response({'error': 'staff_id or staffId is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not job_pricing_id:
                return Response({'error': 'job_pricing_id or jobPricingId is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            logger.debug(f"Looking for staff with ID: {staff_id}")
            logger.debug(f"Looking for job_pricing with ID: {job_pricing_id}")
            
            try:
                staff = Staff.objects.get(id=staff_id)
                logger.debug(f"Found staff: {staff.get_display_name()}")
            except Staff.DoesNotExist:
                logger.error(f"Staff with ID {staff_id} not found. Available staff IDs: {list(Staff.objects.values_list('id', flat=True))}")
                return Response({'error': f'Staff with ID {staff_id} does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                job_pricing = JobPricing.objects.get(id=job_pricing_id)
                logger.debug(f"Found job_pricing: {job_pricing}")
            except JobPricing.DoesNotExist:
                logger.error(f"JobPricing with ID {job_pricing_id} not found")
                return Response({'error': f'JobPricing with ID {job_pricing_id} does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            
            time_entry = TimeEntry.objects.create(
                staff=staff,
                job_pricing=job_pricing,
                date=parse_date(data.get('date')),
                description=data.get('description', ''),
                items=data.get('items', 0),
                minutes_per_item=data.get('minutes_per_item', 0),
                wage_rate=data.get('wage_rate', 0),
                charge_out_rate=data.get('charge_out_rate', 0),
                wage_rate_multiplier=data.get('rate_multiplier', 1.0),
                is_billable=data.get('is_billable', True),
                note=data.get('notes', ''),
                # Remove rate_type field as it doesn't exist in TimeEntry model
            )
            serializer = TimeEntryAPISerializer(time_entry)
            return Response({'time_entry': serializer.data}, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating time entry: {e}")
            logger.error(f"Request data: {data}")
            return Response({'error': 'Failed to create time entry'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, entry_id):
        """Update an existing time entry."""
        try:
            time_entry = TimeEntry.objects.get(id=entry_id)
            data = request.data
            
            # Update fields
            time_entry.description = data.get('description', time_entry.description)
            time_entry.items = data.get('items', time_entry.items)
            time_entry.minutes_per_item = data.get('minutes_per_item', time_entry.minutes_per_item)
            time_entry.wage_rate = data.get('wage_rate', time_entry.wage_rate)
            time_entry.charge_out_rate = data.get('charge_out_rate', time_entry.charge_out_rate)
            time_entry.wage_rate_multiplier = data.get('rate_multiplier', time_entry.wage_rate_multiplier)
            time_entry.is_billable = data.get('is_billable', time_entry.is_billable)
            time_entry.note = data.get('notes', time_entry.note)
            
            if data.get('job_pricing_id'):
                job_pricing = JobPricing.objects.get(id=data.get('job_pricing_id'))
                time_entry.job_pricing = job_pricing
                time_entry.save()
            
            serializer = TimeEntryAPISerializer(time_entry)
            return Response({'time_entry': serializer.data})
            
        except TimeEntry.DoesNotExist:
            return Response({'error': 'Time entry not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating time entry: {e}")
            return Response({'error': 'Failed to update time entry'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, entry_id):
        """Delete a time entry."""
        try:
            time_entry = TimeEntry.objects.get(id=entry_id)
            time_entry.delete()
            return Response({'message': 'Time entry deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except TimeEntry.DoesNotExist:
            return Response({'error': 'Time entry not found'}, status=status.HTTP_404_NOT_FOUND)


class JobsAPIView(APIView):
    """API endpoint to get available jobs for timesheet entries."""
    
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """Get list of active jobs with pricing information."""
        try:
            # Get active jobs with their pricing - filter by status instead of is_active
            # Exclude archived, completed, and rejected jobs
            excluded_statuses = ['archived', 'completed', 'rejected']
            job_pricings = JobPricing.objects.filter(
                job__status__in=['quoting', 'accepted_quote', 'awaiting_materials', 'in_progress', 'on_hold', 'special']
            ).select_related('job').order_by('job__job_number')
            
            if not job_pricings.exists():
                return Response({'jobs': []})
            
            serializer = JobPricingAPISerializer(job_pricings, many=True)
            return Response({'jobs': serializer.data})
        
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            return Response(
                {'error': 'Failed to fetch jobs', 'details': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WeeklyOverviewAPIView(APIView):
    """API endpoint for weekly timesheet overview data."""
    
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """Get weekly overview data for all staff members."""
        try:
            start_date_str = request.query_params.get('start_date')
            
            if not start_date_str:
                # Default to current week
                today = datetime.now().date()
                start_date = today - timedelta(days=today.weekday())
            else:
                start_date = parse_date(start_date_str)
                if not start_date:
                    return Response({'error': 'Invalid start_date format'}, status=status.HTTP_400_BAD_REQUEST)
            
            end_date = start_date + timedelta(days=6)
            
            # Get all staff excluding certain IDs
            excluded_staff_ids = get_excluded_staff()
            staff_members = Staff.objects.exclude(
                Q(is_staff=True) | Q(id__in=excluded_staff_ids)
            ).order_by('last_name', 'first_name')
            
            # Get time entries for the week
            time_entries = TimeEntry.objects.filter(
                date__range=[start_date, end_date],
                staff__in=staff_members
            ).select_related('staff', 'job_pricing__job').order_by('date', 'staff__last_name')
              
            # Organize data by staff and day
            week_data = {}
            for staff in staff_members:
                week_data[str(staff.id)] = {
                    'staff': {
                        'id': str(staff.id),
                        'name': staff.get_display_name() or 'Unknown',
                        'firstName': staff.first_name or '',
                        'lastName': staff.last_name or ''
                    },
                    'days': {},
                    'weeklyTotal': 0
                }
                  
                # Initialize days
                for i in range(7):
                    day_date = start_date + timedelta(days=i)
                    week_data[str(staff.id)]['days'][day_date.strftime('%Y-%m-%d')] = {
                        'date': day_date.strftime('%Y-%m-%d'),
                        'entries': [],
                        'dailyTotal': 0
                    }
            
            # Populate entries
            for entry in time_entries:
                staff_id = str(entry.staff.id)
                date_str = entry.date.strftime('%Y-%m-%d')            
                if staff_id in week_data and date_str in week_data[staff_id]['days']:
                    serializer = TimeEntryAPISerializer(entry)
                    week_data[staff_id]['days'][date_str]['entries'].append(serializer.data)
                    week_data[staff_id]['days'][date_str]['dailyTotal'] += float(entry.hours or 0)
                    week_data[staff_id]['weeklyTotal'] += float(entry.hours or 0)
            
            return Response({
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'staffData': list(week_data.values())
            })
        
        except Exception as e:
            logger.error(f"Error fetching weekly overview: {e}")
            return Response(
                {'error': 'Failed to fetch weekly overview', 'details': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def autosave_timesheet_api(request):
    """Auto-save timesheet entry data (API version of existing autosave functionality)."""
    try:
        data = request.data
        entry_id = data.get('entry_id')
        
        if entry_id:
            # Update existing entry
            time_entry = TimeEntry.objects.get(id=entry_id)
            
            # Update only provided fields
            for field in ['description', 'items', 'minutes_per_item', 'wage_rate', 'charge_out_rate', 'notes']:
                if field in data:
                    setattr(time_entry, field if field != 'notes' else 'note', data[field])
            
            time_entry.save()
            
            return Response({
                'status': 'success',
                'message': 'Entry auto-saved',
                'entry_id': str(time_entry.id)
            })
        else:
            return Response({'status': 'error', 'message': 'No entry ID provided'}, status=400)
            
    except TimeEntry.DoesNotExist:
        return Response({'status': 'error', 'message': 'Entry not found'}, status=404)
    except Exception as e:
        logger.error(f"Autosave error: {e}")
        return Response({'status': 'error', 'message': 'Autosave failed'}, status=500)
