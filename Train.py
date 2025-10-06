import dataclasses
from datetime import date, timedelta
@dataclasses.dataclass(unsafe_hash=True)
class Train:
    """Represents a train's complete state for a single day's decision-making."""
    train_id: int
    is_fit_for_service: bool
    mileage_kms_this_month: float
    has_branding: bool
    branding_days_completed: int
    branding_days_required: int
    branding_expiry_date: date
    predicted_failure_risk: float
    predicted_dirtiness_score: float
    status: str = "UNASSIGNED"

  
    def __init__(self, train_id, is_fit_for_service,mileage_kms_this_month,has_branding,branding_days_required=0, branding_days_completed=0, branding_expiry_date=None,*_,**__):
        self.train_id = int(train_id)
        self.is_fit_for_service = is_fit_for_service
        self.mileage_kms_this_month = int(mileage_kms_this_month)
        self.has_branding = has_branding
        if has_branding :
            self.branding_days_required = int(f"0{branding_days_required}") 
            self.branding_expiry_date = branding_expiry_date
            self.branding_days_completed = int(f"0{branding_days_completed}")
        else:
            self.branding_days_completed=0
            self.branding_expiry_date=None
            self.branding_days_required=0
        self.status = "UNASSIGNED"
        # Predicted scores initialized as floats
        self.predicted_failure_risk = 0.0
        self.predicted_dirtiness_score = 0.0
    
    def toDict(self):
        return {
            'train_id' : self.train_id,
            'is_fit_for_service': self.is_fit_for_service,
            'mileage_kms_this_month' : self.mileage_kms_this_month,
            'has_branding' : self.has_branding,
            'branding_days_required': self.branding_days_required,
            'branding_days_completed': self.branding_days_completed,
            'branding_expiry_date' : self.branding_expiry_date,
            'status' : self.status,
            'predicted_failure_risk': float(self.predicted_failure_risk),
            'predicted_dirtiness_score': float(self.predicted_dirtiness_score)
            
        }

