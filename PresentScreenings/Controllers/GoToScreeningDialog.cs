﻿using System;
using System.Collections.Generic;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Go to screening dialog, created to allow the film info dialog to be
    /// segued from different view controllers.
    /// </summary>

    public abstract class GoToScreeningDialog : NSViewController
    {
        #region Constants
        private const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        private const float _xBetweenLabels = _yBetweenLabels;
        private const float _labelHeight = ControlsFactory.StandardLabelHeight;
        private const float _buttonWidth = _labelHeight;
        #endregion

        #region Application Access
        private static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Private Members
        private static Dictionary<Screening, NSTextField> _labelByfilmScreening;
        #endregion

        #region Constructors
        public GoToScreeningDialog(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Virtual Methods
        public static void DisplayScreeningControls(
            List<Screening> screenings,
            int filmId,
            NSView screeningsView,
            GoToScreeningDelegate goToScreening,
            ref FilmScreeningControl currentScreeningControl)
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
                screeningLabel.StringValue = screening.ToFilmScreeningLabelString(filmId);
                ColorView.SetScreeningColor(screening, screeningLabel);
                screeningsView.AddSubview(screeningLabel);

                // Link the label to the screening.
                _labelByfilmScreening.Add(screening, screeningLabel);

                yScreening -= _yBetweenLabels;
            }
        }

        public static void ScrollScreeningToVisible(Screening screening, NSScrollView scrollView)
        {
            if (_labelByfilmScreening.ContainsKey(screening))
            {
                scrollView.ContentView.ScrollRectToVisible(_labelByfilmScreening[screening].Frame);
            }
        }

        public static void UpdateScreeningControls()
        {
            foreach (var screening in _labelByfilmScreening.Keys)
            {
                ColorView.SetScreeningColor(screening, _labelByfilmScreening[screening]);
                _labelByfilmScreening[screening].StringValue = screening.ToFilmScreeningLabelString();
            }
        }

        /// <summary>
        /// Disable resizing of the given controller's view based on the width
        /// of the given subview.
        /// </summary>
        /// <param name="controller"></param>
        /// <param name="subView"></param>
        public static void DisableResizing(NSViewController controller, NSView subView)
        {
            // Set a dummy name for the subview.
            string controlName = "subview";

            // Get the distance from the top of the subview to the top of the containing view;
            CGRect subViewFrame = subView.Frame;
            nfloat yFromTop = controller.View.Frame.Height - subViewFrame.Height - subViewFrame.Y;

            // Get views being constrained.
            var views = new NSMutableDictionary();
            views.Add(new NSString(controlName), subView);

            // Define format and assemble constraints.
            // (sorry, couln't find an other way to disable resizing)
            var horzFormat = $"|-[{controlName}]-|";
            var horzConstraints = NSLayoutConstraint.FromVisualFormat(horzFormat, NSLayoutFormatOptions.None, null, views);

            var vertFormat = $"V:|-{yFromTop}-[{controlName}]";
            var vertConstraints = NSLayoutConstraint.FromVisualFormat(vertFormat, NSLayoutFormatOptions.None, null, views);

            // Apply constraints.
            NSLayoutConstraint.ActivateConstraints(horzConstraints);
            NSLayoutConstraint.ActivateConstraints(vertConstraints);
        }
        #endregion

        #region Abstract Methods
        public abstract void GoToScreening(Screening screening);
        #endregion

        #region Delegates
        public delegate void GoToScreeningDelegate(Screening screening);
        #endregion
    }
}
