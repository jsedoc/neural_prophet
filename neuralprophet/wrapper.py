from neuralprophet.forecaster import NeuralProphet
import pandas as pd
import logging

log = logging.getLogger("NP.forecaster")


class Prophet(NeuralProphet):
    """
    Prophet wrapper for the NeuralProphet forecaster.

    Parameters
    ----------
    growth: String 'linear', 'logistic' or 'flat' to specify a linear, logistic or
        flat trend.
    changepoints: List of dates at which to include potential changepoints. If
        not specified, potential changepoints are selected automatically.
    n_changepoints: Number of potential changepoints to include. Not used
        if input `changepoints` is supplied. If `changepoints` is not supplied,
        then n_changepoints potential changepoints are selected uniformly from
        the first `changepoint_range` proportion of the history.
    changepoint_range: Proportion of history in which trend changepoints will
        be estimated. Defaults to 0.8 for the first 80%. Not used if
        `changepoints` is specified.
    yearly_seasonality: Fit yearly seasonality.
        Can be 'auto', True, False, or a number of Fourier terms to generate.
    weekly_seasonality: Fit weekly seasonality.
        Can be 'auto', True, False, or a number of Fourier terms to generate.
    daily_seasonality: Fit daily seasonality.
        Can be 'auto', True, False, or a number of Fourier terms to generate.
    holidays: pd.DataFrame with columns holiday (string) and ds (date type)
        and optionally columns lower_window and upper_window which specify a
        range of days around the date to be included as holidays.
        lower_window=-2 will include 2 days prior to the date as holidays. Also
        optionally can have a column prior_scale specifying the prior scale for
        that holiday.
    seasonality_mode: 'additive' (default) or 'multiplicative'.
    seasonality_prior_scale: Not supported for regularisation in NeuralProphet,
        please use the `_reg` args instead.
    holidays_prior_scale: Not supported for regularisation in NeuralProphet,
        please use the `_reg` args instead.
    changepoint_prior_scale: Not supported for regularisation in NeuralProphet,
        please use the `_reg` args instead.
    mcmc_samples: Not required for NeuralProphet
    interval_width: Float, width of the uncertainty intervals provided
        for the forecast. If mcmc_samples=0, this will be only the uncertainty
        in the trend using the MAP estimate of the extrapolated generative
        model. If mcmc.samples>0, this will be integrated over all model
        parameters, which will include uncertainty in seasonality.
    uncertainty_samples: Not required for NeuralProphet.
    stan_backend: Not supported by NeuralProphet.
    """

    def __init__(
        self,
        growth="linear",
        changepoints=None,
        n_changepoints=25,
        changepoint_range=0.8,
        yearly_seasonality="auto",
        weekly_seasonality="auto",
        daily_seasonality="auto",
        holidays=None,
        seasonality_mode="additive",
        seasonality_prior_scale=None,
        holidays_prior_scale=None,
        changepoint_prior_scale=None,
        mcmc_samples=None,
        interval_width=0.80,
        uncertainty_samples=None,
        stan_backend=None,
        **kwargs,
    ):
        # Check for unsupported features
        if seasonality_prior_scale or holidays_prior_scale or changepoint_prior_scale:
            log.info(
                "Using `_prior_scale` is unsupported for regularisation in NeuralProphet, please use the `_reg` args instead."
            )
        if mcmc_samples or uncertainty_samples:
            log.info(
                "Providing the number of samples for Bayesian inference or Uncertainty estimation is not required in NeuralProphet."
            )
        if stan_backend:
            log.info("A stan_backend is not used in NeuralProphet. Please remove the parameter")
        # Run the NeuralProphet function
        super(Prophet, self).__init__(
            growth=growth,
            changepoints=changepoints,
            n_changepoints=n_changepoints,
            changepoints_range=changepoint_range,
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=daily_seasonality,
            seasonality_mode=seasonality_mode,
            prediction_interval=interval_width,
            **kwargs,
        )
        # Handle holidays as events
        if holidays is not None:
            self.add_events(
                events=list(holidays["holiday"].unique()),
                lower_window=holidays["lower_window"].max(),
                upper_window=holidays["upper_window"].max(),
            )
            self.events_df = holidays.copy()
            self.events_df.rename(columns={"holiday": "event"}, inplace=True)
            self.events_df.drop(["lower_window", "upper_window"], axis=1, errors="ignore", inplace=True)

        # Overwrite NeuralProphet properties
        self.name = "Prophet"
        self.history = None

        # Unused properties
        self.train_holiday_names = None

    def validate_inputs(self):
        """
        Validates the inputs to Prophet.
        """
        raise NotImplementedError("Not required in NeuralProphet as all inputs are automatically checked.")

    def validate_column_name(self, name, check_holidays=True, check_seasonalities=True, check_regressors=True):
        """Validates the name of a seasonality, holiday, or regressor.

        Parameters
        ----------
        name: string
        check_holidays: bool check if name already used for holiday
        check_seasonalities: bool check if name already used for seasonality
        check_regressors: bool check if name already used for regressor
        """
        super(Prophet, self)._validate_column_name(
            name=name,
            events=check_holidays,
            seasons=check_seasonalities,
            regressors=check_regressors,
            covariates=check_regressors,
        )

    def setup_dataframe(self, df, initialize_scales=False):
        """Prepare dataframe for fitting or predicting.

        Adds a time index and scales y. Creates auxiliary columns 't', 't_ix',
        'y_scaled', and 'cap_scaled'. These columns are used during both
        fitting and predicting.

        Parameters
        ----------
        df: pd.DataFrame with columns ds, y, and cap if logistic growth. Any
            specified additional regressors must also be present.
        initialize_scales: Boolean set scaling factors in self from df.

        Returns
        -------
        pd.DataFrame prepared for fitting or predicting.
        """
        raise NotImplementedError(
            "Not required in NeuralProphet as the dataframe is automatically prepared using the private `_normalize` function."
        )

    def fit(self, df, **kwargs):
        """Fit the Prophet model.

        This sets self.params to contain the fitted model parameters. It is a
        dictionary parameter names as keys and the following items:
            k (Mx1 array): M posterior samples of the initial slope.
            m (Mx1 array): The initial intercept.
            delta (MxN array): The slope change at each of N changepoints.
            beta (MxK matrix): Coefficients for K seasonality features.
            sigma_obs (Mx1 array): Noise level.
        Note that M=1 if MAP estimation.

        Parameters
        ----------
        df: pd.DataFrame containing the history. Must have columns ds (date
            type) and y, the time series. If self.growth is 'logistic', then
            df must also have a column cap that specifies the capacity at
            each ds.
        kwargs: Additional arguments passed to the optimizing or sampling
            functions in Stan.

        Returns
        -------
        The fitted Prophet object.
        """
        # Check for unsupported features
        if "cap" in df.columns:
            raise NotImplementedError("Saturating forecasts using cap is not supported in NeuralProphet.")
        if "show_progress" in kwargs:
            del kwargs["show_progress"]
        # Handle holidays as events
        if hasattr(self, "events_df"):
            df = self.create_df_with_events(df, self.events_df)
        # Run the NeuralProphet function
        metrics_df = super(Prophet, self).fit(df=df, **kwargs)
        # Store the df for future use like in Prophet
        self.history = df
        return metrics_df

    def predict(self, df=None, **kwargs):
        """Predict using the prophet model.

        Parameters
        ----------
        df: pd.DataFrame with dates for predictions (column ds), and capacity
            (column cap) if logistic growth. If not provided, predictions are
            made on the history.

        Returns
        -------
        A pd.DataFrame with the forecast components.
        """
        if df is None:
            df = self.history.copy()
        df = super(Prophet, self).predict(df=df, **kwargs)
        for column in df.columns:
            # Copy column according to Prophet naming convention
            if "event_" in column:
                df[column.replace("event_", "")] = df[column]
        return df

    def predict_trend(self, df):
        """Predict trend using the prophet model.

        Parameters
        ----------
        df: Prediction dataframe.

        Returns
        -------
        Vector with trend on prediction dates.
        """
        df = super(Prophet, self).predict_trend(self, df, quantile=0.5)
        return df["trend"].to_numpy()

    def make_future_dataframe(self, periods, freq="D", include_history=True, **kwargs):
        """Simulate the trend using the extrapolated generative model.

        Parameters
        ----------
        periods: Int number of periods to forecast forward.
        freq: Any valid frequency for pd.date_range, such as 'D' or 'M'.
        include_history: Boolean to include the historical dates in the data
            frame for predictions.

        Returns
        -------
        pd.Dataframe that extends forward from the end of self.history for the
        requested number of periods.
        """
        # Convert all frequencies to daily
        if freq == "M":
            periods = periods * 30
        # Run the NeuralProphet function
        if hasattr(self, "events_df"):
            # Pass holidays as events
            df_future = super(Prophet, self).make_future_dataframe(
                df=self.history,
                events_df=self.events_df,
                periods=periods,
                n_historic_predictions=include_history,
                **kwargs,
            )
        else:
            df_future = super(Prophet, self).make_future_dataframe(
                df=self.history, periods=periods, n_historic_predictions=include_history, **kwargs
            )
        return df_future

    def add_seasonality(self, name, period, fourier_order, prior_scale=None, mode=None, condition_name=None):
        """Add a seasonal component with specified period, number of Fourier
        components, and prior scale.

        Increasing the number of Fourier components allows the seasonality to
        change more quickly (at risk of overfitting). Default values for yearly
        and weekly seasonalities are 10 and 3 respectively.

        Increasing prior scale will allow this seasonality component more
        flexibility, decreasing will dampen it. If not provided, will use the
        seasonality_prior_scale provided on Prophet initialization (defaults
        to 10).

        Mode can be specified as either 'additive' or 'multiplicative'. If not
        specified, self.seasonality_mode will be used (defaults to additive).
        Additive means the seasonality will be added to the trend,
        multiplicative means it will multiply the trend.

        If condition_name is provided, the dataframe passed to `fit` and
        `predict` should have a column with the specified condition_name
        containing booleans which decides when to apply seasonality.

        Parameters
        ----------
        name: string name of the seasonality component.
        period: float number of days in one period.
        fourier_order: int number of Fourier components to use.
        prior_scale: optional float prior scale for this component.
        mode: optional 'additive' or 'multiplicative'
        condition_name: string name of the seasonality condition.

        Returns
        -------
        The prophet object.
        """
        # Check for unsupported features
        if condition_name:
            log.warn("Conditioning on seasonality is not supported in NeuralProphet.")
        # Set attributes in NeuralProphet config
        self.season_config.mode = mode
        # TODO:
        self.season_config.seasonality_reg = prior_scale
        # Run the NeuralProphet function
        return super(Prophet, self).add_seasonality(name, period, fourier_order)

    def add_regressor(self, name, prior_scale=None, standardize="auto", mode="additive"):
        """Add an additional regressor to be used for fitting and predicting.

        The dataframe passed to `fit` and `predict` will have a column with the
        specified name to be used as a regressor. When standardize='auto', the
        regressor will be standardized unless it is binary. The regression
        coefficient is given a prior with the specified scale parameter.
        Decreasing the prior scale will add additional regularization. If no
        prior scale is provided, self.holidays_prior_scale will be used.
        Mode can be specified as either 'additive' or 'multiplicative'. If not
        specified, self.seasonality_mode will be used. 'additive' means the
        effect of the regressor will be added to the trend, 'multiplicative'
        means it will multiply the trend.

        Parameters
        ----------
        name: string name of the regressor.
        prior_scale: optional float scale for the normal prior. If not
            provided, self.holidays_prior_scale will be used.
        standardize: optional, specify whether this regressor will be
            standardized prior to fitting. Can be 'auto' (standardize if not
            binary), True, or False.
        mode: optional, 'additive' or 'multiplicative'. Defaults to
            self.seasonality_mode.

        Returns
        -------
        The prophet object.
        """
        # Run the NeuralProphet function
        super(Prophet, self).add_future_regressor(name, regularization=prior_scale, normalize=standardize, mode=mode)
        return self

    def add_country_holidays(self, country_name):
        """Add in built-in holidays for the specified country.

        These holidays will be included in addition to any specified on model
        initialization.

        Holidays will be calculated for arbitrary date ranges in the history
        and future. See the online documentation for the list of countries with
        built-in holidays.

        Built-in country holidays can only be set for a single country.

        Parameters
        ----------
        country_name: Name of the country, like 'UnitedStates' or 'US'

        Returns
        -------
        The prophet object.
        """
        super(Prophet, self).add_country_holidays(country_name=country_name)

    def make_seasonality_features(cls, dates, period, series_order, prefix):
        """
        Not used in sample notebooks.
        """
        # TODO

    def construct_holiday_dataframe(self, dates):
        """
        Not used in sample notebooks.
        """
        # TODO

    def make_holiday_features(self, dates, holidays):
        """
        Not used in sample notebooks.
        """
        # TODO

    def make_all_seasonality_features(self, df):
        """
        Not used in sample notebooks.
        """
        # TODO

    def regressor_column_matrix(self, seasonal_features, modes):
        """
        Not used in sample notebooks.
        """
        # TODO

    def add_group_component(self, components, name, group):
        """
        Not used in sample notebooks.
        """
        # TODO

    def parse_seasonality_args(self, name, arg, auto_disable, default_order):
        """
        Not used in sample notebooks.
        """
        # TODO

    def set_auto_seasonalities(self):
        """
        Not used in sample notebooks.
        """
        # TODO

    def plot(
        self,
        fcst,
        ax=None,
        uncertainty=True,
        plot_cap=True,
        xlabel="ds",
        ylabel="y",
        figsize=(10, 6),
        include_legend=False,
    ):
        """Plot the Prophet forecast.

        Parameters
        ----------
        fcst: pd.DataFrame output of self.predict.
        ax: Optional matplotlib axes on which to plot.
        uncertainty: Optional boolean to plot uncertainty intervals.
        plot_cap: Optional boolean indicating if the capacity should be shown
            in the figure, if available.
        xlabel: Optional label name on X-axis
        ylabel: Optional label name on Y-axis
        figsize: Optional tuple width, height in inches.
        include_legend: Optional boolean to add legend to the plot.

        Returns
        -------
        A matplotlib figure.
        """
        log.warn("The attributes `uncertainty`, `plot_cap` and `include_legend` are not supported by NeuralProphet")
        super(Prophet, self).plot(fcst=fcst, ax=ax, xlabel=xlabel, ylabel=ylabel, figsize=figsize)

    def plot_components(self, fcst, uncertainty=True, plot_cap=True, weekly_start=0, yearly_start=0, figsize=None):
        """Plot the Prophet forecast components.

        Will plot whichever are available of: trend, holidays, weekly
        seasonality, and yearly seasonality.

        Parameters
        ----------
        fcst: pd.DataFrame output of self.predict.
        uncertainty: Optional boolean to plot uncertainty intervals.
        plot_cap: Optional boolean indicating if the capacity should be shown
            in the figure, if available.
        weekly_start: Optional int specifying the start day of the weekly
            seasonality plot. 0 (default) starts the week on Sunday. 1 shifts
            by 1 day to Monday, and so on.
        yearly_start: Optional int specifying the start day of the yearly
            seasonality plot. 0 (default) starts the year on Jan 1. 1 shifts
            by 1 day to Jan 2, and so on.
        figsize: Optional tuple width, height in inches.

        Returns
        -------
        A matplotlib figure.
        """
        # TODO


def plot_plotly(m, forecast, **kwargs):
    # Run the NeuralProphet plotting function
    fig = m.plot(forecast, plotting_backend="plotly", **kwargs)
    return fig


def plot_components_plotly(m, forecast, **kwargs):
    # Run the NeuralProphet plotting function
    fig = m.plot_components(forecast, plotting_backend="plotly", **kwargs)
    return fig


def plot_yearly(**kwargs):
    raise NotImplementedError(
        "Plotting yearly seasonality is not implemented in NeuralProphet. Please use the `plot` function."
    )


# TODO: Plot parameters wrapper
