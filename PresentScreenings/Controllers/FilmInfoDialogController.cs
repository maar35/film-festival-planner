﻿// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
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
        const float _xMargin = ControlsFactory.HorizontalMargin;
        const float _yMargin = ControlsFactory.BigVerticalMargin;
        const float _yBetweenViews = ControlsFactory.VerticalPixelsBetweenViews;
        const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        const float _labelHeight = ControlsFactory.StandardLabelHeight;
        const float _buttonWidth = ControlsFactory.StandardButtonWidth;
        const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        const float _summaryBoxHeight = 300;
        #endregion

        #region Private Variables
        private float _contentWidth;
        private float _yCurr;
        private Film _film;
        private FilmInfo _filmInfo;
        private CGRect _dialogFrame;
        private NSTextField _summaryField;
        private NSFont _originalSummaryFieldFont;
        private NSColor _originalSummaryFieldColor;
        private bool _summaryFieldFormatIsOriginal;
        private NSScrollView _summaryScrollView;
        private NSButton _linkButton;
        private NSButton _cancelButton;
        private FilmScreeningControl _currentScreeningControl;
        private NSView _sampleView;
        #endregion

        #region Properties
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        public static GoToScreeningDialog Presentor { get; set; }
        public bool BehaveAsPopup { get; set; } = false;
        public bool DialogShouldClose { get; set; } = false;
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
            App.filmInfoController = this;

            // Get the selected film.
            _film = ((IScreeningProvider)Presentor).CurrentFilm;

            // Get the downloaded film info if present.
            _filmInfo = ViewController.GetFilmInfo(_film.FilmId);

            // Set basis dimensions.
            _dialogFrame = View.Frame;
            _yCurr = (float)_dialogFrame.Height;
            _contentWidth = (float)_dialogFrame.Width - 2 * _xMargin;

            // Create the film title label.
            _yCurr -= _yMargin;
            CreateFilmTitleLabel(ref _yCurr);

            if (!BehaveAsPopup)
            {
                // Create the film article link.
                _yCurr -= _yBetweenViews;
                CreateFilmArticleLink(ref _yCurr);
            }

            // Create the film summary box.
            _yCurr -= _yBetweenViews;
            CreateFilmSummaryBox(ref _yCurr);

            if (!BehaveAsPopup)
            {
                // Create the screenings scroll view.
                    _yCurr -= _yBetweenViews;
                    CreateScreeningsScrollView(ref _yCurr);

                // Create the cancel button.
                _yCurr = _yMargin + _buttonHeight + _yBetweenViews;   // temp
                _yCurr -= _yBetweenViews;
                CreateCancelButton(ref _yCurr);
            }

            // Disable resizing.
            Presentor.DisableResizing(this, _sampleView);
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate that we're gone.
            App.filmInfoController = null;
        }
        #endregion

        #region Private Methods
        void CreateFilmTitleLabel(ref float yCurr)
        {
            yCurr -= _labelHeight;
            var rect = new CGRect(_xMargin, yCurr, _contentWidth, _labelHeight);
            var filmTitleLabel = ControlsFactory.NewStandardLabel(rect);
            filmTitleLabel.StringValue = _film.Title;
            filmTitleLabel.Font = NSFont.BoldSystemFontOfSize(NSFont.SystemFontSize);
            View.AddSubview(filmTitleLabel);

            // Set sample view used to disable resizing.
            _sampleView = filmTitleLabel;
        }

        void CreateScreeningsScrollView(ref float yCurr)
        {
            // Get the screenings of the selected film.
            var screenings = ViewController.FilmScreenings(_film.FilmId);

            // Create the screenings view.
            var xScreenings = screenings.Count * (_labelHeight + _yBetweenLabels);
            var screeningsViewFrame = new CGRect(0, 0, _contentWidth, xScreenings);
            var screeningsView = new NSView(screeningsViewFrame);

            // Create the scroll view.
            var scrollViewHeight = yCurr - _yBetweenViews - _buttonHeight - _yMargin;
            yCurr -= (float)scrollViewHeight;
            var scrollViewFrame = new CGRect(_xMargin, yCurr, _contentWidth, scrollViewHeight);
            var scrollView = ControlsFactory.NewStandardScrollView(scrollViewFrame, screeningsView);
            View.AddSubview(scrollView);

            // Display the screenings.
            GoToScreeningDialog.DisplayScreeningControls(screenings, screeningsView, GoToScreening, ref _currentScreeningControl);

            // Scroll to the selected screening.
            GoToScreeningDialog.ScrollScreeningToVisible(App.Controller.CurrentScreening, scrollView);
        }

        void CreateFilmArticleLink(ref float yCurr)
        {
            yCurr -= _buttonHeight;
            var rect = new CGRect(_xMargin, yCurr, _contentWidth, _buttonHeight);
            _linkButton = ControlsFactory.NewStandardButton(rect);
            _linkButton.LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            _linkButton.Title = _film.Url;
            _linkButton.Enabled &= !FilmInfoIsAvailable();
            _linkButton.Tag = _film.FilmId;
            _linkButton.Action = new ObjCRuntime.Selector("VisitUrl:");

            //NSMutableAttributedString attrStr = new NSMutableAttributedString("Alpha Go hyperlink");
            //var range = new NSRange(8, 9); // Range for "hyperlink" word
            //var url = new NSUrl("https://IFFR.com/nl/2018/films/alpha-go");
            //label.AccessibilityUrl = url;
            //var font = label.Font; // _myLablel is an instance of NSClickableURLTextField class
            //// We have to setup paragraph if we want to keep original alignment and line break node
            //var paragraph = new NSMutableParagraphStyle();
            //paragraph.LineBreakMode = label.Cell.LineBreakMode;
            //paragraph.Alignment = label.Alignment;
            //attrStr.BeginEditing();
            ////attrStr.AddAttribute(NSAttributedString.CreateWithHTML(url, range);
            //attrStr.AddAttribute((NSString)"color", NSColor.Blue, range);
            ////attrStr.AddAttribute(NSAttributedString.UnderlineStyleAttributeName, new NSNumber(1), range);
            ////attrStr.AddAttribute(NSAttributedString.FontAttributeName, font, new NSRange(0, attrStr.Length)); // Set font for entire string
            ////attrStr.AddAttribute(NSAttributedString.ParagraphStyleAttributeName, paragraph, new NSRange(0, attrStr.Length)); // Optional
            //attrStr.EndEditing();
            //label.AttributedStringValue = attrStr;

            View.AddSubview(_linkButton);
        }

        void CreateFilmSummaryBox(ref float yCurr)
        {
            // Create a text box to contain the film info.
            float summaryBoxHeight = BehaveAsPopup ? yCurr - _yMargin : _summaryBoxHeight;
            var docRect = new CGRect(0, 0, _contentWidth, _summaryBoxHeight);
            _summaryField = new NSTextField(docRect);
            InitiateSummaryFieldText();
            var fit = _summaryField.SizeThatFits(_summaryField.Frame.Size);
            _summaryField.SetFrameSize(fit);

            // Create a scroll view to display the film info.
            yCurr -= summaryBoxHeight;
            var rect = new CGRect(_xMargin, yCurr, _contentWidth, summaryBoxHeight);
            _summaryScrollView = ControlsFactory.NewStandardScrollView(rect, _summaryField);
            _summaryScrollView.ContentView.ScrollToPoint(new CGPoint(0, 0));
            View.AddSubview(_summaryScrollView);
        }

        void CreateCancelButton(ref float yCurr)
        {
            yCurr -= _buttonHeight;
            var cancelButtonRect = new CGRect(_xMargin, yCurr, _buttonWidth, _buttonHeight);
            _cancelButton = ControlsFactory.NewCancelButton(cancelButtonRect);
            _cancelButton.Title = "Close";
            _cancelButton.Action = new ObjCRuntime.Selector("CancelGotoScreening:");
            View.AddSubview(_cancelButton);
        }

        void InitiateSummaryFieldText()
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
                var popoverToText = new Dictionary<bool, string> { };
                popoverToText[true] = $"Sorry, no description found for {_film}";
                popoverToText[false] = "Please, hit the URL button above to get film information from the web site.";
                SetSummaryFieldText(popoverToText[BehaveAsPopup], true);
            }
        }

        void SetSummaryFieldText(string text, bool alternativeFormat = false)
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

        bool FilmInfoIsAvailable()
        {
            return ViewController.FilmInfoIsAvailable(_filmInfo);
        }

        void VisitUrl()
        {
            string summary = string.Empty;
            var catagory = _film.Catagory;
            FilmInfo filmInfo;
            var url = _film.Url;
            _summaryScrollView.BackgroundColor = NSColor.WindowBackground;
            var request = WebRequest.Create(url) as HttpWebRequest;
            try
            {
                filmInfo = WebUtility.TryParseUrlSummary(request, url, catagory, _film.FilmId);
                if (filmInfo != null)
                {
                    _filmInfo = filmInfo;
                    _filmInfo.InfoStatus = Film.FilmInfoStatus.Complete;
                    summary = filmInfo.ToString();
                    _linkButton.Title = url;
                }
            }
            catch (WebException ex)
            {
                FilmInfo.AddNewFilmInfo(_film.FilmId, Film.FilmInfoStatus.UrlError);
                _summaryScrollView.BackgroundColor = NSColor.SystemPinkColor;
                summary = $"Web exception in {url}\n\n" + ex.ToString();
            }
            catch (UnparseblePageException ex)
            {
                FilmInfo.AddNewFilmInfo(_film.FilmId, Film.FilmInfoStatus.ParseError);
                _summaryScrollView.BackgroundColor = NSColor.SystemYellowColor;
                var builder = new StringBuilder();
                builder.AppendLine($"URL {url} could not be parsed.");
                builder.AppendLine("===");
                builder.Append(ex.Message);
                summary = builder.ToString();
            }
            finally
            {
                SetSummaryFieldText(summary);
                var fit = _summaryField.SizeThatFits(_summaryField.Frame.Size);
                _summaryField.SetFrameSize(fit);
            }
            if (App.FilmsDialogController != null)
            {
                var controller = App.FilmsDialogController;
                controller.FilmRatingTableView.ReloadData();
                controller.SelectFilm(_film);
            }
        }

        private void GoToScreening(Screening screening)
        {
            Presentor.GoToScreening(screening);
            if (DialogShouldClose)
            {
                ClosePopOver();
            }
        }

        void ClosePopOver()
        {
            Presentor.DismissViewController(this);
        }
        #endregion

        #region Custom Actions
        [Action("CancelGotoScreening:")]
        void CancelGotoScreening(NSObject sender)
        {
            ClosePopOver();
        }

        [Action("VisitUrl:")]
        void VisitUrl(NSObject sender)
        {
            VisitUrl();
        }
        #endregion
    }
}
