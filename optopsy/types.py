"""Type definitions for Optopsy strategy parameters."""

from typing import Literal, Optional, TypedDict, Union

import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)


class Commission(BaseModel):
    """Commission fee structure for options and stock trades.

    Supports multiple broker fee models:
    - Flat per-contract: ``Commission(per_contract=0.65)``
    - Base fee + per-contract: ``Commission(per_contract=0.65, base_fee=9.99)``
    - Min fee + per-contract: ``Commission(per_contract=0.65, min_fee=4.95)``
    - Per-share for stock legs: ``Commission(per_contract=0.65, per_share=0.005)``
    """

    model_config = ConfigDict(extra="forbid")

    per_contract: float = Field(0.0, ge=0)
    per_share: float = Field(0.0, ge=0)
    base_fee: float = Field(0.0, ge=0)
    min_fee: float = Field(0.0, ge=0)


class TargetRange(BaseModel):
    """Generic range selector with target, min, and max values.

    Used for per-leg delta targeting (and extensible to other Greeks).
    All values are unsigned (0-1 for delta).
    """

    model_config = ConfigDict(extra="forbid")

    target: float = Field(gt=0, le=1)
    min: float = Field(gt=0, le=1)
    max: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def check_ordering(self):
        if self.min > self.target:
            raise ValueError(f"min ({self.min}) must be <= target ({self.target})")
        if self.target > self.max:
            raise ValueError(f"target ({self.target}) must be <= max ({self.max})")
        return self


class StrategyParamsDict(TypedDict, total=False):
    """Common parameters for all option strategies (TypedDict for Unpack[] annotations).

    All fields are optional to allow partial parameter specification.
    """

    # Timing parameters
    max_entry_dte: int
    exit_dte: int
    exit_dte_tolerance: int
    dte_interval: int

    # Filtering parameters
    min_bid_ask: float

    # Delta grouping interval
    delta_interval: float

    # Per-leg delta targeting (optional)
    leg1_delta: Optional[TargetRange]
    leg2_delta: Optional[TargetRange]
    leg3_delta: Optional[TargetRange]
    leg4_delta: Optional[TargetRange]

    # Pre-computed signal dates (optional).
    # DataFrames with (underlying_symbol, quote_date) pairs indicating
    # valid dates for entry/exit.  Use signals.signal_dates() to generate.
    entry_dates: Optional[pd.DataFrame]
    exit_dates: Optional[pd.DataFrame]

    # Slippage settings
    slippage: Literal["mid", "spread", "liquidity", "per_leg"]
    fill_ratio: float
    reference_volume: int
    per_leg_slippage: float

    # Side
    side: Literal["long", "short"]

    # Commission
    commission: Optional[Union["Commission", float]]

    # Early exit thresholds (P&L-based)
    stop_loss: float
    take_profit: float

    # Time-based early exit
    max_hold_days: int

    # Output control
    raw: bool
    drop_nan: bool


class CalendarStrategyParamsDict(StrategyParamsDict):
    """Parameters for calendar and diagonal spread strategies (TypedDict for Unpack[]).

    Extends StrategyParamsDict with additional timing parameters for
    front and back month legs.
    """

    # Additional timing parameters for calendar/diagonal strategies
    front_dte_min: int
    front_dte_max: int
    back_dte_min: int
    back_dte_max: int


class StrategyParams(BaseModel):
    """Pydantic model for validating and defaulting strategy parameters.

    This is the single source of truth for parameter defaults and validation.
    Fields with defaults are applied automatically when not provided by the user.
    Uses ``extra="forbid"`` to catch typos in parameter names.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    # Timing parameters (strict rejects float/bool coercion)
    max_entry_dte: int = Field(90, gt=0, strict=True)
    exit_dte: int = Field(0, ge=0, strict=True)
    exit_dte_tolerance: int = Field(0, ge=0, strict=True)
    dte_interval: int = Field(7, gt=0, strict=True)

    # Filtering parameters (strict float enforced by validate_strict_float below)
    min_bid_ask: float = Field(0.05, gt=0)

    # Delta grouping interval (always-on, non-optional)
    delta_interval: float = Field(0.05, gt=0)

    # Per-leg delta targeting (optional)
    leg1_delta: Optional[TargetRange] = None
    leg2_delta: Optional[TargetRange] = None
    leg3_delta: Optional[TargetRange] = None
    leg4_delta: Optional[TargetRange] = None

    # Pre-computed signal dates (optional)
    entry_dates: Optional[pd.DataFrame] = None
    exit_dates: Optional[pd.DataFrame] = None

    # Slippage settings
    slippage: Literal["mid", "spread", "liquidity", "per_leg"] = "mid"
    fill_ratio: Union[int, float] = Field(0.5, ge=0, le=1)
    reference_volume: int = Field(1000, gt=0, strict=True)
    per_leg_slippage: Union[int, float] = Field(0.073, ge=0, le=1)

    # Side (optional — not consumed by core pipeline, reserved for future use)
    side: Optional[Literal["long", "short"]] = None

    # Commission
    commission: Optional[Union[Commission, float]] = None

    # Early exit thresholds (P&L-based)
    stop_loss: Optional[float] = Field(None, lt=0)
    take_profit: Optional[float] = Field(None, gt=0)

    # Time-based early exit
    max_hold_days: Optional[int] = Field(None, gt=0, strict=True)

    # Output control — strict bool (rejects int)
    raw: StrictBool = False
    drop_nan: StrictBool = True

    @field_validator("commission", mode="before")
    @classmethod
    def validate_commission(cls, v):
        if v is None:
            return None
        if isinstance(v, Commission):
            return v
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return Commission(per_contract=float(v))
        if isinstance(v, dict):
            return Commission(**v)
        raise ValueError("commission must be a float, dict, or Commission instance")

    @field_validator("min_bid_ask", "delta_interval", mode="before")
    @classmethod
    def validate_strict_float(cls, v, info):
        if v is not None and not isinstance(v, float):
            raise ValueError(
                f"Invalid setting for {info.field_name}, must be positive float type"
            )
        return v

    @field_validator("stop_loss", "take_profit", mode="before")
    @classmethod
    def validate_exit_threshold(cls, v, info):
        if v is not None and not isinstance(v, float):
            raise ValueError(
                f"Invalid setting for {info.field_name}, must be a float or None"
            )
        return v

    @field_validator("fill_ratio", "per_leg_slippage", mode="before")
    @classmethod
    def validate_strict_number(cls, v, info):
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise ValueError(
                f"Invalid setting for {info.field_name}, must be a number (int/float) or None"
            )
        return v

    @field_validator("entry_dates", "exit_dates", mode="before")
    @classmethod
    def validate_dates_dataframe(cls, v, info):
        if v is None:
            return v
        if not isinstance(v, pd.DataFrame):
            raise ValueError(
                f"Invalid setting for {info.field_name}, must be a DataFrame or None"
            )
        required = {"underlying_symbol", "quote_date"}
        missing = required - set(v.columns)
        if missing:
            raise ValueError(
                f"{info.field_name} missing required columns: {missing}. "
                f"Expected at least: underlying_symbol, quote_date."
            )
        return v

    @model_validator(mode="after")
    def check_exit_dte_ordering(self):
        if self.max_entry_dte is not None and self.exit_dte >= self.max_entry_dte:
            raise ValueError(
                f"exit_dte ({self.exit_dte}) must be < "
                f"max_entry_dte ({self.max_entry_dte})"
            )
        return self


class CalendarStrategyParams(StrategyParams):
    """Pydantic model for calendar/diagonal spread parameter validation.

    Extends StrategyParams with front/back DTE fields, overrides defaults
    for calendar-specific behavior, and adds cross-field DTE range validators.
    """

    # Calendar strategies don't use max_entry_dte — override to Optional
    max_entry_dte: Optional[int] = Field(None, gt=0, strict=True)

    # Calendar strategies default to exit_dte=7 instead of 0
    exit_dte: int = Field(7, ge=0, strict=True)

    # Additional timing parameters for calendar/diagonal strategies
    front_dte_min: int = Field(20, gt=0, strict=True)
    front_dte_max: int = Field(40, gt=0, strict=True)
    back_dte_min: int = Field(50, gt=0, strict=True)
    back_dte_max: int = Field(90, gt=0, strict=True)

    @model_validator(mode="after")
    def check_dte_ranges(self):
        if self.front_dte_min > self.front_dte_max:
            raise ValueError(
                f"front_dte_min ({self.front_dte_min}) must be <= "
                f"front_dte_max ({self.front_dte_max})"
            )

        if self.back_dte_min > self.back_dte_max:
            raise ValueError(
                f"back_dte_min ({self.back_dte_min}) must be <= "
                f"back_dte_max ({self.back_dte_max})"
            )

        if self.front_dte_max >= self.back_dte_min:
            raise ValueError(
                f"front_dte_max ({self.front_dte_max}) must be < "
                f"back_dte_min ({self.back_dte_min}) to avoid overlapping ranges"
            )

        return self


class SimulatorParams(BaseModel):
    """Pydantic model for validating simulator parameters."""

    capital: Union[int, float] = Field(gt=0)
    quantity: int = Field(gt=0, strict=True)
    max_positions: int = Field(gt=0, strict=True)
    multiplier: int = Field(gt=0, strict=True)

    @field_validator("capital", mode="before")
    @classmethod
    def validate_capital(cls, v):
        # Reject booleans and non-numeric types for capital
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(
                "Invalid setting for capital, must be a positive int or float"
            )
        return v
