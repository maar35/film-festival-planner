// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Combine title view controler, manages a sheet which allows the user to
    /// combine multiple films into one.
    /// The title of the film wich should become the film title of all
    /// screenings is chosen by means of a set of radio buttons.
    /// </summary>

    public partial class CombineTitlesSheetController : NSViewController
	{
        #region Private Constants
        const float _xMargin = ControlsFactory.HorizontalMargin;
        const float _xDistance = ControlsFactory.HorizontalPixelsBetweenControls;
        const float _labelWidth = 25;
        const float _yMargin = ControlsFactory.SmallVerticalMargin;
        const float _yControlsDistance = 1;
        const float _controlsHeight = ControlsFactory.StandardLabelHeight;
        const float _topLabelsHeigh = 17;
        const float _yToplabelsDistance = 8;
        const float _bottomControlsHeight = 13;
        const float _yXcodeControlsMargin = 20;
        //const float _magicTwenty = 20;
        #endregion

        #region Private Variables
        float _scrollViewWidth;
        nuint[] _filmIndexes;
        List<int> _filmIds;
        int _mainFilmId;
        NSScrollView _titlesScrollView;
        NSView _titlesDocumentView;
        #endregion

        #region Application Access
        static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public FilmRatingDialogController Presentor;
        #endregion

        #region Constructors
        public CombineTitlesSheetController(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Override Methods
        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Tell the app delegate we're alive.
            _app.CombineTitleController = this;

            // Initialize.
            var filmList = Presentor.FilmRatingTableView.SelectedRows;
            _filmIndexes = filmList.ToArray();
            _mainFilmId = Presentor.GetFilmByIndex(_filmIndexes[0]).FilmId;
            _filmIds = new List<int>();
            _scrollViewWidth = (float)(View.Frame.Width - 2 * _xMargin);

            // Create the document view displaying the film title radio buttons.
            nfloat titlesViewWidth = _scrollViewWidth - 2 * _xMargin;
            nfloat titlesViewHeight = filmList.Count * _controlsHeight + (filmList.Count - 1) *_yControlsDistance;
            CGRect titlesViewFrame = new CGRect(0, 0, titlesViewWidth, titlesViewHeight);
            _titlesDocumentView = new NSView(titlesViewFrame);

            // Create the scroll view.
            CreateTitlesScrollView();

            // Set constraints of the in-code generated UI elements.
            SetConstraints();
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate we're gone.
            _app.CombineTitleController = null;
        }
        #endregion

        #region Private Methods
        private void CreateTitlesScrollView()
        {
            // Create the scroll view to display the title radio buttons.
            nfloat yScrollView = 2 * _yXcodeControlsMargin + _bottomControlsHeight;
            nfloat scrollViewHeight = View.Frame.Height - _yXcodeControlsMargin - 2 * (_topLabelsHeigh + _yToplabelsDistance) - yScrollView;
            CGRect scrollViewFrame = new CGRect(_xMargin, yScrollView, _scrollViewWidth, scrollViewHeight);
            _titlesScrollView = ControlsFactory.NewStandardScrollView(scrollViewFrame, _titlesDocumentView);
            View.AddSubview(_titlesScrollView);

            // Create labels with the film titles.
            PopulateTitlesDocumentView();
        }

        private void PopulateTitlesDocumentView()
        {
            // Define dimensions.
            nfloat radioButtonWidth = _titlesDocumentView.Frame.Width - 2 * _xMargin - _xDistance - _labelWidth;
            nfloat xLabel = _titlesDocumentView.Frame.Width - _xMargin - _labelWidth;

            // Create a vertical list of radiobuttons.
            nfloat yCurr = _titlesDocumentView.Frame.Height;
            foreach (var filmIndex in _filmIndexes)
            {
                // Add an item to the film id list.
                Film film = Presentor.GetFilmByIndex(filmIndex);
                _filmIds.Add(film.FilmId);

                // Adjust the vertical position with control height.
                yCurr -= _controlsHeight;

                // Create a radio button for the film title.
                CGRect radioButtonRect = new CGRect(_xMargin, yCurr, radioButtonWidth, _controlsHeight);
                NSButton titleRadioButton = new NSButton(radioButtonRect);
                titleRadioButton.SetButtonType(NSButtonType.Radio);
                titleRadioButton.Action = new ObjCRuntime.Selector("MainTitleChanged:");
                titleRadioButton.State = film.FilmId == _mainFilmId ? NSCellStateValue.On : NSCellStateValue.Off;
                titleRadioButton.Tag = film.FilmId;
                titleRadioButton.Title = film.Title;
                _titlesDocumentView.AddSubview(titleRadioButton);

                // Create a label for the rating.
                CGRect labelRect = new CGRect(xLabel, yCurr, _labelWidth, _controlsHeight);
                NSTextField ratingLabel = ControlsFactory.NewStandardLabel(labelRect);
                ratingLabel.Alignment = NSTextAlignment.Right;
                ratingLabel.StringValue = Presentor.GetFilmByIndex(filmIndex).Rating.ToString();
                _titlesDocumentView.AddSubview(ratingLabel);

                // Ajust the vertical position with the distance between two controls.
                yCurr -= _yControlsDistance;
            }
        }

        /// <summary>
        /// Sets the constraints as to make the sheet unresizable.
        /// </summary>
        private void SetConstraints()
        {
            nfloat yFromTop = _yXcodeControlsMargin + 2 * (_topLabelsHeigh + _yToplabelsDistance);
            Presentor.DisableResizing(_titlesScrollView, "scroller", yFromTop);
        }

        private void CloseSheet()
        {
            Presentor.DismissViewController(this);
        }
        #endregion

        #region Custom Actions
        partial void AcceptSheet(Foundation.NSObject sender)
        {
            RaiseSheetAccepted();
            CloseSheet();
        }

        partial void CancelSheet(Foundation.NSObject sender)
        {
            RaiseSheetCanceled();
            CloseSheet();
        }

        [Action("MainTitleChanged:")]
        void MainTitleChanged(NSObject sender)
        {
            var radioButton = sender as NSButton;
            _mainFilmId = (int)radioButton.Tag;
        }
        #endregion

        #region Events
        public EventHandler SheetAccepted;

        internal void RaiseSheetAccepted()
        {
            SheetAccepted?.Invoke(this, new CombineTitlesEventArgs(_filmIds, _mainFilmId));
        }

        public EventHandler SheetCanceled;

        internal void RaiseSheetCanceled()
        {
            SheetCanceled?.Invoke(this, EventArgs.Empty);
        }
        #endregion
    }
}
