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
        const float _xMargin = 20;
        const float _xScrollerMargin = 5;
        const float _cancelButtonWidth = 94;
        const float _xControlsDistance = 8;
        const float _yMargin = 8;
        const float _labelHeight = 19;
        const float _screeningHeight = 46;
        const float _buttonHeight = 32;
        const float _yControlsDistance = 2;
        const float _separateHeight = 8;
        const float _yScreeningSpace = _screeningHeight + _yControlsDistance;
        const string _enterKey = "\r";
        const string _escapeKey = "\x1b";
        #endregion

        #region Private Variables
        nfloat _yCurr;
        List<Screening> _screenings;
        List<string> _distinctTitles;
        CGRect _sheetFrame;
        CGRect _scrollerFrame;
        CGRect _screeningsFrame;
        NSView _screeningsView;
        Dictionary<bool, string> _enabledToLabelTitle;
        #endregion

        #region Application Access
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public FilmRatingDialogController Presentor;
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
            _screenings = Presentor.GetScreeningsByFilmId(film.FilmId);

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
            nfloat scrollViewHeight = _sheetFrame.Height - 2 *_yMargin - 2 * _labelHeight - _yControlsDistance - 2 * _separateHeight - _buttonHeight;
            _scrollerFrame = new CGRect(scrollViewX, scrollViewY, scrollViewWidth, scrollViewHeight);

            nfloat docViewWidth = _sheetFrame.Width - 2 * _xScrollerMargin;
            nfloat screeningListHeight = _screenings.Count * _yScreeningSpace + 2 * _separateHeight;
            nfloat docViewHeight = scrollViewHeight > screeningListHeight ? scrollViewHeight : screeningListHeight;
            _screeningsFrame = new CGRect(0, 0, docViewWidth, docViewHeight);
        }

        void CreateTitleLabels()
        {
            nfloat labelWidth = _sheetFrame.Width - 2 * _xMargin;

            _yCurr -= _labelHeight;

            NSTextField titleLabel = new NSTextField(new CGRect(_xMargin, _yCurr, labelWidth, _labelHeight));
            titleLabel.Editable = false;
            titleLabel.Font = NSFont.BoldSystemFontOfSize(NSFont.SystemFontSize);
            titleLabel.BackgroundColor = NSColor.WindowBackground;
            titleLabel.Bordered = false;
            titleLabel.StringValue = "Uncombine film";
            View.AddSubview(titleLabel);

            _yCurr -= _labelHeight + _yControlsDistance;

            NSTextField instructionLabel = new NSTextField(new CGRect(_xMargin, _yCurr, labelWidth, _labelHeight));
            instructionLabel.Editable = false;
            instructionLabel.Font = NSFont.LabelFontOfSize(NSFont.LabelFontSize);
            instructionLabel.BackgroundColor = NSColor.WindowBackground;
            instructionLabel.Bordered = false;
            instructionLabel.StringValue = "Create multiple films, one per distinct screening title";
            View.AddSubview(instructionLabel);

            // Make the sheet unresizable (sorry, couln't find an other way).

            //// Get views being constrained
            var views = new NSMutableDictionary();
            views.Add(new NSString("title"), titleLabel);

            // Define format and assemble constraints
            var horzFormat = "|-[title]-|";
            var horzConstraints = NSLayoutConstraint.FromVisualFormat(horzFormat, NSLayoutFormatOptions.None, null, views);

            var vertFormat = "V:|-[title]";
            var vertConstraints = NSLayoutConstraint.FromVisualFormat(vertFormat, NSLayoutFormatOptions.None, null, views);

            // Apply constraints
            NSLayoutConstraint.ActivateConstraints(horzConstraints);
            NSLayoutConstraint.ActivateConstraints(vertConstraints);
        }

        void CreateScrollView()
        {
            _yCurr -= _scrollerFrame.Height + _separateHeight;

            _screeningsView = new NSView(_screeningsFrame);

            NSScrollView scrollView = new NSScrollView(_scrollerFrame);
            scrollView.BackgroundColor = NSColor.WindowBackground;
            scrollView.BorderType = NSBorderType.BezelBorder;
            scrollView.DocumentView = _screeningsView;
            scrollView.ContentView.ScrollToPoint(new CGPoint(0, _screeningsFrame.Height));
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
            NSButton cancelButton = Presentor.CreateCancelButton(cancelButtonRect);
            cancelButton.Action = new ObjCRuntime.Selector("CancelUncombine:");
            View.AddSubview(cancelButton);
        }

        void CreateUncombineButton()
        {
            nfloat spliButtonX = _xMargin + _cancelButtonWidth + _xControlsDistance;
            nfloat splitButtonWidth = _sheetFrame.Width - spliButtonX - _xMargin;
            CGRect splitButtonRect = new CGRect(spliButtonX, _yMargin, splitButtonWidth, _buttonHeight);
            NSButton splitButton = new NSButton(splitButtonRect);
            splitButton.BezelStyle = NSBezelStyle.Rounded;
            splitButton.SetButtonType(NSButtonType.MomentaryPushIn);
            splitButton.Action = new ObjCRuntime.Selector("UncombineFilms:");
            int filmCount = _distinctTitles.Count();
            bool enable = filmCount > 1;
            splitButton.Title = string.Format(_enabledToLabelTitle[enable], filmCount);
            splitButton.Enabled = enable;
            splitButton.KeyEquivalent = _enterKey;
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
