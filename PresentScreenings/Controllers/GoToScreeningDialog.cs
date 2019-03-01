using System;
using System.Collections.Generic;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Go to screening dialog, created to allow the film info dialog to be
    /// segued from different view controllers.
    /// </summary>

    public abstract class GoToScreeningDialog : NSViewController
    {
        #region Constants
        const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        const float _xBetweenLabels = _yBetweenLabels;
        const float _labelHeight = ControlsFactory.StandardLabelHeight;
        const float _buttonWidth = _labelHeight;
        #endregion

        #region Application Access
        static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Private Members
        static Dictionary<Screening, NSTextField> _labelByfilmScreening;
        #endregion

        #region Constructors
        public GoToScreeningDialog(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Virtual Methods
        public static void DisplayScreeningControls(List<Screening> screenings, NSView screeningsView,
            GoToScreeningDelegate goToScreening, ref FilmScreeningControl currentScreeningControl)
        {
            _labelByfilmScreening = new Dictionary<Screening, NSTextField> { };
            var yScreening = screeningsView.Frame.Height;
            var contentWidth = screeningsView.Frame.Width;
            foreach (var screening in screenings)
            {
                float xScreening = 0;
                yScreening -= _labelHeight;

                // Create the screening info button.
                var buttonRect = new CGRect(xScreening, yScreening, _buttonWidth, _labelHeight);
                var infoButton = new FilmScreeningControl(buttonRect, screening);
                infoButton.ReDraw();
                infoButton.ScreeningInfoAsked += (sender, e) => goToScreening(screening);
                if (screening == _app.Controller.CurrentScreening)
                {
                    currentScreeningControl = infoButton;
                    currentScreeningControl.Selected = true;
                }
                screeningsView.AddSubview(infoButton);
                xScreening += _buttonWidth + _xBetweenLabels;

                // Create the screening label.
                var labelRect = new CGRect(xScreening, yScreening, contentWidth - xScreening, _labelHeight);
                var screeningLabel = ControlsFactory.CreateStandardLabel(labelRect);
                screeningLabel.StringValue = screening.ToFilmScreeningLabelString();
                ColorView.SetScreeningColor(screening, screeningLabel);
                screeningsView.AddSubview(screeningLabel);
                _labelByfilmScreening.Add(screening, screeningLabel);

                yScreening -= _yBetweenLabels;
            }
        }

        static public void UpdateScreeningControls()
        {
            foreach (var screening in _labelByfilmScreening.Keys)
            {
                ColorView.SetScreeningColor(screening, _labelByfilmScreening[screening]);
                _labelByfilmScreening[screening].StringValue = screening.ToFilmScreeningLabelString();
            }
        }
        #endregion

        #region Abstract Methods
        public abstract void GoToScreening(Screening screening);
        #endregion

        #region Delagates
        public delegate void GoToScreeningDelegate(Screening screening);
        #endregion
    }
}
