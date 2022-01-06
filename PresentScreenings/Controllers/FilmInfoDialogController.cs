﻿// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Text;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film info dialog controller, present film information from the web site
    /// if available. Otherwise allow to search the web sitr.
    /// Optionally displays a list of the screenings of the current film, with
    /// buttons to navigate to the screening.
    /// </summary>

    public partial class FilmInfoDialogController : NSViewController
    {
        #region Constants
        private const float _xMargin = ControlsFactory.HorizontalMargin;
        private const float _yMargin = ControlsFactory.BigVerticalMargin;
        private const float _yBetweenViews = ControlsFactory.VerticalPixelsBetweenViews;
        private const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        private const float _labelHeight = ControlsFactory.StandardLabelHeight;
        private const float _buttonWidth = ControlsFactory.StandardButtonWidth;
        private const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        private const float _imageSide = ControlsFactory.StandardButtomImageSide;
        private const float _imageButtonWidth = ControlsFactory.StandardImageButtonWidth;
        private const float _summaryBoxHeight = 300;
        private const int _maxVisibleScreeningCount = 5;
        private const float _scrollViewHeight = _maxVisibleScreeningCount * (_labelHeight + _yBetweenLabels);
        #endregion

        #region Private Variables
        private float _contentWidth;
        private float _yCurr;
        private Film _film;
        private FilmInfo _filmInfo;
        private NSTextField _summaryField;
        private NSFont _originalSummaryFieldFont;
        private NSColor _originalSummaryFieldColor;
        private bool _summaryFieldFormatIsOriginal;
        private NSScrollView _summaryScrollView;
        private NSButton _cancelButton;
        private FilmScreeningControl _currentScreeningControl;
        private NSView _sampleView;
        #endregion

        #region Properties
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        public static GoToScreeningDialog Presentor { get; set; }
        public bool BehaveAsPopover { get; set; } = false;
        public bool UseTitleBackground { get; set; } = false;
        #endregion

        #region Constructors
        public FilmInfoDialogController(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Override Methods
        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Tell the app delegate that we're alive.
            App.FilmInfoController = this;

            // Inactivate screenings view actions.
            App.Controller.RunningPopupsCount++;

            // Get the selected film.
            _film = ((IScreeningProvider)Presentor).CurrentFilm;

            // Get the downloaded film info if present.
            _filmInfo = ViewController.GetFilmInfo(_film.FilmId);

            // Set basis dimensions.
            var dialogFrame = View.Frame;
            _yCurr = (float)dialogFrame.Height;
            _contentWidth = (float)dialogFrame.Width - 2 * _xMargin;

            // Create the controls that were not defined in Xcode.
            PopulatieDialogView();

            // Disable resizing.
            Presentor.DisableResizing(this, _sampleView);
        }

        public override void ViewDidDisappear()
        {
            base.ViewDidDisappear();

            // Tell the app delegate that we're gone.
            App.FilmInfoController = null;

            // Tell the main view controller we're gone.
            App.Controller.RunningPopupsCount--;
        }
        #endregion

        #region Public Methods
        public void CloseDialog()
        {
            Presentor.DismissViewController(this);
        }
        #endregion

        #region Private Methods
        private void PopulatieDialogView()
        {
            // Create the film title label.
            _yCurr -= _yMargin;
            CreateFilmTitleLabel();

            // Populate the rest of the dialog dependant of its behaviour.
            if (BehaveAsPopover)
            {
                PopulateAsPopover();
            }
            else
            {
                PopulateAsModal();
            }
        }

        private void PopulateAsPopover()
        {
            // Create the film summary box.
            _yCurr -= _yBetweenViews;
            CreateFilmSummaryBox(_yCurr - _yMargin);
        }

        private void PopulateAsModal()
        {
            // Create the film summary box.
            _yCurr -= _yBetweenViews;
            CreateFilmSummaryBox(_yCurr - _scrollViewHeight - 2 * _yBetweenViews - _buttonHeight - _yMargin);

            // Create the screenings scroll view.
            _yCurr -= _yBetweenViews;
            CreateScreeningsScrollView();

            // Create the buttons at the bottom of the view.
            _yCurr -= _yBetweenViews;
            CreateBottomButtons();
        }

        private void CreateFilmTitleLabel()
        {
            _yCurr -= _labelHeight;
            var rect = new CGRect(_xMargin, _yCurr, _contentWidth, _labelHeight);
            var filmTitleLabel = ControlsFactory.NewStandardLabel(rect, UseTitleBackground);
            filmTitleLabel.StringValue = _film.Title;
            filmTitleLabel.Font = NSFont.BoldSystemFontOfSize(NSFont.SystemFontSize);
            View.AddSubview(filmTitleLabel);

            // Set sample view used to disable resizing.
            _sampleView = filmTitleLabel;
        }

        private void CreateFilmSummaryBox(float boxHeight)
        {
            // Create a text box to contain the film info.
            var docRect = new CGRect(0, 0, _contentWidth, _summaryBoxHeight);
            _summaryField = new NSTextField(docRect);
            InitiateSummaryFieldText();
            var fit = _summaryField.SizeThatFits(_summaryField.Frame.Size);
            _summaryField.SetFrameSize(fit);

            // Create a scroll view to display the film info.
            _yCurr -= boxHeight;
            var rect = new CGRect(_xMargin, _yCurr, _contentWidth, boxHeight);
            _summaryScrollView = ControlsFactory.NewStandardScrollView(rect, _summaryField);
            _summaryScrollView.ContentView.ScrollToPoint(new CGPoint(0, 0));
            View.AddSubview(_summaryScrollView);
        }

        private void CreateScreeningsScrollView()
        {
            // Get the screenings of the selected film.
            var screenings = new List<Screening> { };
            var programIds = _film.FilmInfo.CombinationProgramIds;
            if (programIds.Count == 0)
            {
                screenings = _film.FilmScreenings;
            }
            else
            {
                foreach (var programId in programIds)
                {
                    var program = ViewController.GetFilmById(programId);
                    screenings.AddRange(program.FilmScreenings);
                }
            }

            // Create the screenings view.
            var yScreenings = screenings.Count * (_labelHeight + _yBetweenLabels);
            var screeningsViewFrame = new CGRect(0, 0, _contentWidth, yScreenings);
            var screeningsView = new NSView(screeningsViewFrame);

            // Create the scroll view.
            _yCurr -= _scrollViewHeight;
            var scrollViewFrame = new CGRect(_xMargin, _yCurr, _contentWidth, _scrollViewHeight);
            var scrollView = ControlsFactory.NewStandardScrollView(scrollViewFrame, screeningsView);
            View.AddSubview(scrollView);

            // Display the screenings.
            GoToScreeningDialog.DisplayScreeningControls(screenings, screeningsView, GoToScreening, ref _currentScreeningControl);

            // Scroll to the selected screening.
            GoToScreeningDialog.ScrollScreeningToVisible(App.Controller.CurrentScreening, scrollView);
        }

        private void CreateBottomButtons()
        {
            var xCurr = _xMargin + _contentWidth;

            // Create the close button.
            xCurr -= _buttonWidth;
            var cancelButtonRect = new CGRect(xCurr, _yMargin, _buttonWidth, _buttonHeight);
            _cancelButton = ControlsFactory.NewCancelButton(cancelButtonRect);
            _cancelButton.Title = "Close";
            _cancelButton.Action = new ObjCRuntime.Selector("CancelGotoScreening:");
            View.AddSubview(_cancelButton);

            // Create the website button.
            xCurr -= _imageButtonWidth;
            NSButton websiteButton = ControlsFactory.NewVisitWebsiteButton(xCurr, _yMargin, _film);
            websiteButton.Enabled = true;
            View.AddSubview(websiteButton);
        }

        private void InitiateSummaryFieldText()
        {
            _summaryFieldFormatIsOriginal = true;
            _originalSummaryFieldFont = _summaryField.Font;
            _originalSummaryFieldColor = _summaryField.TextColor;
            _summaryField.Editable = false;
            _summaryField.Selectable = true;
            if (FilmInfoIsAvailable())
            {
                SetSummaryFieldText(_filmInfo.ToString());
            }
            else
            {
                const string text = "Sorry, the URL button above is under construction.";
                SetSummaryFieldText(text, true);
            }
        }

        private void SetSummaryFieldText(string text, bool alternativeFormat = false)
        {
            if (alternativeFormat && _summaryFieldFormatIsOriginal)
            {
                _summaryField.Selectable = false;
                _summaryField.Font = NSFont.LabelFontOfSize(24);
                _summaryField.TextColor = NSColor.LightGray;
                _summaryFieldFormatIsOriginal = false;
            }
            else if (! alternativeFormat && ! _summaryFieldFormatIsOriginal)
            {
                _summaryField.Selectable = true;
                _summaryField.Font = _originalSummaryFieldFont;
                _summaryField.TextColor = _originalSummaryFieldColor;
                _summaryFieldFormatIsOriginal = true;
            }
            _summaryField.StringValue = text;
        }

        private bool FilmInfoIsAvailable()
        {
            return ViewController.FilmInfoIsAvailable(_filmInfo);
        }

        private void GoToScreening(Screening screening)
        {
            Presentor.GoToScreening(screening);
            CloseDialog();
        }
        #endregion

        #region Custom Actions
        [Action("VisitFilmWebsite:")]
        void VisitFilmWebsite(NSObject sender)
        {
            ViewController.VisitFilmWebsite(_film);
        }

        [Action("CancelGotoScreening:")]
        void CancelGotoScreening(NSObject sender)
        {
            CloseDialog();
        }
        #endregion
    }
}
