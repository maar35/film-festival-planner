// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Uncombine title sheet controller, manages a sheet wich allows the user
    /// to split a film with multiple screening titles into one film per unique
    /// screening title.
    /// </summary>

    public partial class UncombineTitlesSheetController : NSViewController
    {
        #region Private Constants
        const float _xMargin = ControlsFactory.HorizontalMargin;
        const float _xScrollerMargin = ControlsFactory.SmallHorizontalMargin;
        const float _cancelButtonWidth = ControlsFactory.StandardButtonWidth;
        const float _xControlsDistance = ControlsFactory.HorizontalPixelsBetweenControls;
        const float _yMargin = ControlsFactory.SmallVerticalMargin;
        const float _labelHeight = ControlsFactory.StandardLabelHeight;
        const float _screeningHeight = ControlsFactory.BigScreeningLabelHeight;
        const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        const float _yLabelsDistance = ControlsFactory.VerticalPixelsBetweenLabels;
        const float _separateHeight = ControlsFactory.WideVerticalPixelsBetweenLabels;
        const float _yScreeningSpace = _screeningHeight + _yLabelsDistance;
        #endregion

        #region Private Variables
        private nfloat _yCurr;
        private List<Screening> _screenings;
        private List<string> _distinctTitles;
        private CGRect _sheetFrame;
        private CGRect _scrollerFrame;
        private CGRect _screeningsFrame;
        private NSView _screeningsView;
        private NSView _sampleView;
        private Dictionary<bool, string> _enabledToLabelTitle;
        #endregion

        #region Application Access
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public FilmRatingDialogController Presentor { get; set; }
        #endregion

        #region Constructors
        public UncombineTitlesSheetController(IntPtr handle) : base(handle)
        {
            _enabledToLabelTitle = new Dictionary<bool, string> { };
            _enabledToLabelTitle[true] = "Split into {0} films";
            _enabledToLabelTitle[false] = "Can't uncombine {0} distinct title";
        }
        #endregion

        #region Override Methods
        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Tell the app delegate we're alive.
            App.UncombineTitleController = this;

            // Populate the screenings list.
            nuint filmIndex = (nuint)Presentor.FilmRatingTableView.SelectedRow;
            Film film = Presentor.GetFilmByIndex(filmIndex);
            _screenings = film.FilmScreenings;

            // Populate the distinct titles list.
            _distinctTitles = _screenings.Select(s => s.ScreeningTitle).Distinct().ToList();

            // Define dimensions of frames of scroller view and document view.
            SetDimensions();

            // Create title labels.
            CreateTitleLabels();

            // Create a scroll view to dispay the screenings.
            CreateScrollView();

            // Display the screenings of the selected film.
            DisplayScreenings();

            // Create the cancel button.
            CreateCancelButton();

            // Create the uncombine button.
            CreateUncombineButton();

            // Disable resizing.
            GoToScreeningDialog.DisableResizing(this, _sampleView);
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate we're gone.
            App.UncombineTitleController = null;
        }
        #endregion

        #region Private Methods
        void SetDimensions()
        {
            _sheetFrame = View.Frame;
            _yCurr = _sheetFrame.Height - _yMargin;

            nfloat scrollViewX = _xMargin + _xScrollerMargin;
            nfloat scrollViewY = _separateHeight + _buttonHeight + _separateHeight;
            nfloat scrollViewWidth = _sheetFrame.Width - 2 * (_xMargin + _xScrollerMargin);
            nfloat scrollViewHeight = _sheetFrame.Height - 2 * _yMargin - 2 * _labelHeight - _yLabelsDistance - 2 * _separateHeight - _buttonHeight;
            _scrollerFrame = new CGRect(scrollViewX, scrollViewY, scrollViewWidth, scrollViewHeight);

            nfloat docViewWidth = _sheetFrame.Width - 2 * _xScrollerMargin;
            nfloat screeningListHeight = _screenings.Count * _yScreeningSpace + 2 * _separateHeight;
            nfloat docViewHeight = scrollViewHeight > screeningListHeight ? scrollViewHeight : screeningListHeight;
            _screeningsFrame = new CGRect(0, 0, docViewWidth, docViewHeight);
        }

        void CreateTitleLabels()
        {
            nfloat labelWidth = _sheetFrame.Width - 2 * _xMargin;

            // Create the window title label.
            _yCurr -= _labelHeight;
            var titleLabelRect = new CGRect(_xMargin, _yCurr, labelWidth, _labelHeight);
            var titleLabel = ControlsFactory.NewStandardLabel(titleLabelRect);
            titleLabel.Font = ControlsFactory.StandardBoldFont;
            titleLabel.StringValue = "Uncombine film";
            View.AddSubview(titleLabel);

            // Create the instruction label.
            _yCurr -= _labelHeight + _yLabelsDistance;
            var instructionLabelRect = new CGRect(_xMargin, _yCurr, labelWidth, _labelHeight);
            var instructionLabel = ControlsFactory.NewStandardLabel(instructionLabelRect);
            instructionLabel.Font = NSFont.LabelFontOfSize(NSFont.LabelFontSize);
            instructionLabel.StringValue = "Create multiple films, one per distinct screening title";
            View.AddSubview(instructionLabel);

            // Set sample view used to disable resizing.
            _sampleView = titleLabel;
        }

        void CreateScrollView()
        {
            _yCurr -= _scrollerFrame.Height + _separateHeight;

            _screeningsView = new NSView(_screeningsFrame);

            var scrollView = ControlsFactory.NewStandardScrollView(_scrollerFrame, _screeningsView);
            View.AddSubview(scrollView);
        }

        void DisplayScreenings()
        {
            nfloat screeningWidth = _screeningsFrame.Width - 2 * _xScrollerMargin;
            nfloat yCurr = _screeningsFrame.Height - _separateHeight;
            foreach (var screening in _screenings)
            {
                yCurr -= _yScreeningSpace;
                var screeningRect = new CGRect(_xScrollerMargin, yCurr, screeningWidth, _screeningHeight);
                ScreeningLabel label = new ScreeningLabel(screeningRect, screening, true);
                _screeningsView.AddSubview(label);
            }
        }

        void CreateCancelButton()
        {
            CGRect cancelButtonRect = new CGRect(_xMargin, _yMargin, _cancelButtonWidth, _buttonHeight);
            NSButton cancelButton = ControlsFactory.NewCancelButton(cancelButtonRect);
            cancelButton.Action = new ObjCRuntime.Selector("CancelUncombine:");
            View.AddSubview(cancelButton);
        }

        void CreateUncombineButton()
        {
            nfloat splitButtonX = _xMargin + _cancelButtonWidth + _xControlsDistance;
            nfloat splitButtonWidth = _sheetFrame.Width - splitButtonX - _xMargin;
            CGRect splitButtonRect = new CGRect(splitButtonX, _yMargin, splitButtonWidth, _buttonHeight);
            NSButton splitButton = ControlsFactory.NewStandardButton(splitButtonRect);
            splitButton.Action = new ObjCRuntime.Selector("UncombineFilms:");
            int filmCount = _distinctTitles.Count();
            bool enable = filmCount > 1;
            splitButton.Enabled = enable;
            splitButton.Title = string.Format(_enabledToLabelTitle[enable], filmCount);
            splitButton.KeyEquivalent = ControlsFactory.EnterKey;
            View.AddSubview(splitButton);
        }

        void CloseSheet()
        {
            Presentor.DismissViewController(this);
        }
        #endregion

        #region Custom Actions
        [Action("CancelUncombine:")]
        void CancelPopover(NSObject sender)
        {
            CloseSheet();
        }

        [Action("UncombineFilms:")]
        void UncombineFilms(NSObject sender)
        {
            //Presentor.UncombineScreeningTitles(_screenings);
            RaiseSheetAccepted();
            CloseSheet();
        }
        #endregion

        #region Events
        public EventHandler SheetAccepted;

        internal void RaiseSheetAccepted()
        {
            SheetAccepted?.Invoke(this, new UncombineTitlesEventArgs(_screenings));
        }

        #endregion
    }
}
