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
            // Initialize the dictionary to find labels by screening.
            _labelByfilmScreening = new Dictionary<Screening, NSTextField> { };

            // Initialize dimensions.
            var xLabel = _buttonWidth + _xBetweenLabels;
            var yScreening = screeningsView.Frame.Height;
            var contentWidth = screeningsView.Frame.Width;
            var buttonRect = new CGRect(0, yScreening, _buttonWidth, _labelHeight);
            var labelRect = new CGRect(xLabel, yScreening, contentWidth - xLabel, _labelHeight);

            foreach (var screening in screenings)
            {
                // Update the vertical position.
                yScreening -= _labelHeight;

                // Create the screening info button.
                buttonRect.Y = yScreening;
                var infoButton = new FilmScreeningControl(buttonRect, screening);
                infoButton.ReDraw();
                infoButton.ScreeningInfoAsked += (sender, e) => goToScreening(screening);
                if (screening == _app.Controller.CurrentScreening)
                {
                    currentScreeningControl = infoButton;
                    currentScreeningControl.Selected = true;
                }
                screeningsView.AddSubview(infoButton);

                // Create the screening label.
                labelRect.Y = yScreening;
                var screeningLabel = ControlsFactory.NewStandardLabel(labelRect);
                screeningLabel.StringValue = screening.ToFilmScreeningLabelString();
                ColorView.SetScreeningColor(screening, screeningLabel);
                screeningsView.AddSubview(screeningLabel);

                // Link the label to the screening.
                _labelByfilmScreening.Add(screening, screeningLabel);

                yScreening -= _yBetweenLabels;
            }
        }

        static public void ScrollScreeningToVisible(Screening screening, NSScrollView scrollView)
        {
            if (_labelByfilmScreening.ContainsKey(screening))
            {
                scrollView.ContentView.ScrollRectToVisible(_labelByfilmScreening[screening].Frame);
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
