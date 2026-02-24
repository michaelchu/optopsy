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
    max_otm_pct: float
    otm_pct_interval: float
    min_bid_ask: float

    # Greeks filtering (optional)
    delta_min: Optional[float]
    delta_max: Optional[float]

    # Greeks grouping (optional)
    delta_interval: Optional[float]

    # Pre-computed signal dates (optional).
    # DataFrames with (underlying_symbol, quote_date) pairs indicating
    # valid dates for entry/exit.  Use signals.apply_signal() to generate.
    entry_dates: Optional[pd.DataFrame]
    exit_dates: Optional[pd.DataFrame]

    # Slippage settings
    slippage: Literal["mid", "spread", "liquidity"]
    fill_ratio: float
    reference_volume: int

    # Side
    side: Literal["long", "short"]

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
    """Pydantic model for validating common strategy parameters.

    All fields are optional to allow partial parameter specification.
    Mirrors the StrategyParamsDict TypedDict but with runtime validation.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    # Timing parameters (strict rejects float/bool coercion)
    max_entry_dte: Optional[int] = Field(None, gt=0, strict=True)
    exit_dte: Optional[int] = Field(None, ge=0, strict=True)
    exit_dte_tolerance: Optional[int] = Field(None, ge=0, strict=True)
    dte_interval: Optional[int] = Field(None, gt=0, strict=True)

    # Filtering parameters (strict float enforced by validate_strict_float below)
    max_otm_pct: Optional[float] = Field(None, gt=0)
    otm_pct_interval: Optional[float] = Field(None, gt=0)
    min_bid_ask: Optional[float] = Field(None, gt=0)

    # Greeks filtering (optional) — accepts int or float
    delta_min: Optional[Union[int, float]] = None
    delta_max: Optional[Union[int, float]] = None

    # Greeks grouping (optional) — accepts int or float
    delta_interval: Optional[Union[int, float]] = None

    # Pre-computed signal dates (optional)
    entry_dates: Optional[pd.DataFrame] = None
    exit_dates: Optional[pd.DataFrame] = None

    # Slippage settings
    slippage: Optional[Literal["mid", "spread", "liquidity"]] = None
    fill_ratio: Optional[Union[int, float]] = Field(None, ge=0, le=1)
    reference_volume: Optional[int] = Field(None, gt=0, strict=True)

    # Side
    side: Optional[Literal["long", "short"]] = None

    # Output control — strict bool (rejects int)
    raw: Optional[StrictBool] = None
    drop_nan: Optional[StrictBool] = None

    @field_validator("max_otm_pct", "otm_pct_interval", "min_bid_ask", mode="before")
    @classmethod
    def validate_strict_float(cls, v, info):
        if v is not None and not isinstance(v, float):
            raise ValueError(
                f"Invalid setting for {info.field_name}, must be positive float type"
            )
        return v

    @field_validator("delta_min", "delta_max", "delta_interval", "fill_ratio", mode="before")
    @classmethod
    def validate_strict_number(cls, v, info):
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise ValueError(
                f"Invalid setting for {info.field_name}, must be float type or None"
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


class CalendarStrategyParams(StrategyParams):
    """Pydantic model for calendar/diagonal spread parameter validation.

    Extends StrategyParams with front/back DTE fields and cross-field validators.
    """

    # Additional timing parameters for calendar/diagonal strategies
    front_dte_min: Optional[int] = Field(None, gt=0, strict=True)
    front_dte_max: Optional[int] = Field(None, gt=0, strict=True)
    back_dte_min: Optional[int] = Field(None, gt=0, strict=True)
    back_dte_max: Optional[int] = Field(None, gt=0, strict=True)

    @model_validator(mode="after")
    def check_dte_ranges(self):
        if self.front_dte_min is not None and self.front_dte_max is not None:
            if self.front_dte_min > self.front_dte_max:
                raise ValueError(
                    f"front_dte_min ({self.front_dte_min}) must be <= "
                    f"front_dte_max ({self.front_dte_max})"
                )

        if self.back_dte_min is not None and self.back_dte_max is not None:
            if self.back_dte_min > self.back_dte_max:
                raise ValueError(
                    f"back_dte_min ({self.back_dte_min}) must be <= "
                    f"back_dte_max ({self.back_dte_max})"
                )

        if self.front_dte_max is not None and self.back_dte_min is not None:
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
