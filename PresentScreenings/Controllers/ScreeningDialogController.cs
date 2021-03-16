// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using System.Linq;
using Foundation;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening dialog controler, manages a dialog which displays extra information
    /// of a screening and in which editable screening properties can be changed.
    /// </summary>

    public partial class ScreeningDialogController : GoToScreeningDialog, IScreeningProvider
    {
        #region Constants
        const float _xMargin = ControlsFactory.HorizontalMargin;
        const float _yMargin = ControlsFactory.BigVerticalMargin;
        const float _yBetweenViews = ControlsFactory.VerticalPixelsBetweenViews;
        const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        const float _labelHeight = ControlsFactory.StandardLabelHeight;
        const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        const float _yControlsDistance = ControlsFactory.VerticalPixelsBetweenControls;
        #endregion

        #region Private Members
        private nfloat _yCurr;
        private Screening _screening;
        private ScreeningControl _senderControl;
        private ViewController _presentor;
        private List<Screening> _filmScreenings;
        private FilmScreeningControl _screeningInfoControl;
        private Dictionary<string, AttendanceCheckbox> _attendanceCheckboxByFilmFan;
        private NSView _sampleSubView;
        #endregion

        #region Properties
        public ViewController Presentor
        {
            get => _presentor;
            set => _presentor = (ViewController)value;
        }
        #endregion

        #region Interface Implementation Properties
        public Screening CurrentScreening => Presentor.Plan.CurrScreening;
        public List<Screening> Screenings => Presentor.Plan.CurrScreening.FilmScreenings;
        public Film CurrentFilm => ViewController.GetFilmById(CurrentScreening.FilmId);
        #endregion

        #region Constructors
        public ScreeningDialogController(IntPtr handle) : base(handle)
        {
            _filmScreenings = new List<Screening> { };
            _attendanceCheckboxByFilmFan = new Dictionary<string, AttendanceCheckbox> { };
        }
        #endregion

        #region Override Methods
        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Tell the presentor we're alive.
            _presentor.ScreeningInfoDialog = this;
            _presentor.RunningPopupsCount += 1;

            // Initialize the list of screenings.
            _filmScreenings = _screening.FilmScreenings;

            // Populate the controls.
            SetControlValues();
            CreateFilmFanControls();

            // Create the screenings scroll view.
            CreateScreeningsScrollView();

            // Disable Resizing.
            DisableResizing(this, _sampleSubView);
        }

        public override void ViewWillDisappear()
        {
            // Tell the presentor we're gone.
            _presentor.RunningPopupsCount--;
            if (_presentor.RunningPopupsCount == 0)
            {
                _presentor.ScreeningInfoDialog = null;
            }
        }

        public override void PrepareForSegue(NSStoryboardSegue segue, NSObject sender)
        {
            base.PrepareForSegue(segue, sender);

            // Take action based on the segue name
            switch (segue.Identifier)
            {
                case "ScreeningToFilmInfo":
                    var filmInfoModal = segue.DestinationController as FilmInfoDialogController;
                    FilmInfoDialogController.Presentor = this;
                    filmInfoModal.BehaveAsPopover = true;
                    filmInfoModal.UseTitleBackground = true;
                break;
            }
        }

        public override void GoToScreening(Screening screening)
        {
            _presentor.GoToScreening(screening);
            CloseDialog();
        }
        #endregion

        #region Private Methods
        private void SetControlValues()
        {
            // Populate the Info Button.
            var imageByAvailability = new Dictionary<bool, NSImage> { };
            imageByAvailability[true] = _filmInfoButton.Image;
            imageByAvailability[false] = _filmInfoButton.AlternateImage;
            var isAvailable = ViewController.FilmInfoIsAvailable(_screening.Film);
            _filmInfoButton.Image = imageByAvailability[isAvailable];
            _filmInfoButton.Action = new ObjCRuntime.Selector("TryShowFilmInfo:");

            // Select the sending screening control in the screenings table.
            _senderControl.Selected = true;

            // Populate the labels.
            _labelTitle.StringValue = $"{_screening.FilmTitle} ({_screening.Film.MinutesString})";
            if (_screening.Extra != string.Empty)
            {
                _labelTitle.StringValue += " (+ " + _screening.Extra + ")";
            }
            _labelScreen.StringValue = _screening.Screen.ParseName;
            _labelTime.StringValue = _screening.ToLongTimeString();
            _labelPresent.StringValue = _screening.AttendeesString();

            // Populate the checkboxes.
            _checkboxTicketsBought.Activated += (s, e) => ToggleTicketsBought();
            _checkboxTicketsBought.State = ViewController.GetNSCellStateValue(_screening.TicketsBought);
            _checkboxSoldOut.Activated += (s, e) => ToggleSoldOut();
            _checkboxSoldOut.State = ViewController.GetNSCellStateValue(_screening.SoldOut);
        }

        private void CreateFilmFanControls()
        {
            // Clone the Rating combo box.
            var comboBoxFrame = _comboboxRating.Frame;
            var comboBoxFont = _comboboxRating.Font;

            // Dispose the original Rating combo box.
            _comboboxRating.RemoveFromSuperview();
            _comboboxRating.Dispose();

            // Initialize the vertical postion of run-time created controls.
            _yCurr = comboBoxFrame.Y;

            // Initialze values to construct the Attendance checkboxes.
            var checkBoxFrame = _checkboxIAttend.Frame;
            var checkBoxShift = comboBoxFrame.Y - checkBoxFrame.Y;

            // Dispose the original Attendance check box.
            _checkboxIAttend.RemoveFromSuperview();
            _checkboxIAttend.Dispose();

            nfloat yDelta = 0;
            foreach (var filmfan in ScreeningInfo.FilmFans)
            {
                // Update the vertical position.
                _yCurr -= yDelta;
                if (yDelta == 0)
                {
                    yDelta = comboBoxFrame.Height + _yControlsDistance;
                }

                // Create the Rating combobox for this film fan.
                comboBoxFrame.Y = _yCurr;
                var fanRatingComboBox = ControlsFactory.NewRatingComboBox(comboBoxFrame, comboBoxFont);
                fanRatingComboBox.EditingBegan += (s, e) => HandleFilmFanRatingEditingBegan(fanRatingComboBox, filmfan);
                fanRatingComboBox.EditingEnded += (s, e) => HandleFilmFanRatingEditingEnded(fanRatingComboBox, filmfan);
                fanRatingComboBox.StringValue = ViewController.GetFilmFanFilmRating(_screening.FilmId, filmfan).ToString();
                View.AddSubview(fanRatingComboBox);

                // Create the Attendance checkbox for this film fan.
                checkBoxFrame.Y = _yCurr - checkBoxShift;
                var fanCheckbox = new AttendanceCheckbox(checkBoxFrame);
                fanCheckbox.Title = filmfan;
                fanCheckbox.State = AttendanceCheckbox.GetAttendanceState(_screening.FilmFanAttends(filmfan));
                fanCheckbox.Activated += (s, e) => ToggleAttendance(filmfan);
                View.AddSubview(fanCheckbox);

                // Link the checkbox to the film fan.
                _attendanceCheckboxByFilmFan.Add(filmfan, fanCheckbox);
            }
        }

        private void CreateScreeningsScrollView()
        {
            // Get the screenings of the selected film.
            var screenings = _filmScreenings;

            // Create the screenings view.
            var xScreenings = screenings.Count * (_labelHeight + _yBetweenLabels);
            var contentWidth = this.View.Frame.Width - 2 * _xMargin;
            var screeningsViewFrame = new CGRect(0, 0, contentWidth, xScreenings);
            var screeningsView = new NSView(screeningsViewFrame);

            // Create the scroll view.
            _yCurr -= _yBetweenViews;
            var scrollViewHeight = _yCurr - _yBetweenViews - _buttonHeight - _yMargin;
            _yCurr -= scrollViewHeight;
            var scrollViewFrame = new CGRect(_xMargin, _yCurr, contentWidth, scrollViewHeight);
            var scrollView = ControlsFactory.NewStandardScrollView(scrollViewFrame, screeningsView, true);
            View.AddSubview(scrollView);

            // Display the screenings.
            DisplayScreeningControls(screenings, screeningsView, GoToScreening, ref _screeningInfoControl);

            // Scroll to the selected screening.
            ScrollScreeningToVisible(CurrentScreening, scrollView);

            // Set sample view used to disable resizing.
            _sampleSubView = scrollView;
        }

        private void CloseDialog()
        {
            _presentor.DismissViewController(this);
        }

        private void HandleFilmFanRatingEditingBegan(NSComboBox comboBox, string filmFan)
        {
            _closeButton.Enabled = false;
        }

        private void HandleFilmFanRatingEditingEnded(NSComboBox comboBox, string filmFan)
        {
            int filmId = _screening.FilmId;
            Func<string, string> getControlValue = r => GetNewValueFromComboBox(comboBox, r);
            _presentor.SetRatingIfValid(comboBox, getControlValue, filmId, filmFan);
            _closeButton.Enabled = true;
        }

        private string GetNewValueFromComboBox(NSComboBox comboBox, string oldString)
        {
            string comboBoxString = comboBox.StringValue;
            if (comboBox.SelectedValue == null)
            {
                if (!comboBox.Values.Any(v => v.ToString() == comboBoxString))
                {
                    comboBox.StringValue = oldString;
                    throw new IllegalRatingException(comboBoxString);
                }
            }
            else
            {
                comboBoxString = comboBox.SelectedValue.ToString();
            }
            return comboBoxString;
        }

        private void TryShowFilmInfo(NSObject sender)
        {
            var film = _screening.Film;
            if (ViewController.FilmInfoIsAvailable(film))
            {
                PerformSegue("ScreeningToFilmInfo", sender);
            }
            else
            {
                Presentor.PerformSegue("ScreeningsToFilmInfo", sender);
                CloseDialog();
            }
        }
        #endregion

        #region Public Methods
        public void PopulateDialog(ScreeningControl sender)
        {
            _senderControl = sender;
            _screening = sender.Screening;
        }

        public void ToggleTicketsBought()
        {
            _screening.TicketsBought = !_screening.TicketsBought;
            UpdateAttendances();
        }

        public void ToggleSoldOut()
        {
            _screening.SoldOut = !_screening.SoldOut;
            UpdateAttendances();
        }

        public void ToggleAttendance(string filmFan)
        {
            _screening.ToggleFilmFanAttendance(filmFan);
            UpdateAttendances();
            var attendanceState = AttendanceCheckbox.GetAttendanceState(_screening.FilmFanAttends(filmFan));
            _attendanceCheckboxByFilmFan[filmFan].State = attendanceState;
        }

        public void UpdateAttendances()
        {
            _labelPresent.StringValue = _screening.AttendeesString();
            _presentor.UpdateAttendanceStatus(_screening);
            _presentor.ReloadScreeningsView();
            UpdateScreeningControls();
            _screeningInfoControl.ReDraw();
        }
        #endregion

        #region Custom Actions
        partial void AcceptDialog(Foundation.NSObject sender)
        {
            RaiseDialogAccepted();
            CloseDialog();
        }

        partial void CancelDialog(Foundation.NSObject sender)
        {
            RaiseDialogCanceled();
            CloseDialog();
        }

        partial void ToggleTicketsBought(NSObject sender)
        {
            ToggleTicketsBought();
            _checkboxTicketsBought.State = ViewController.GetNSCellStateValue(_screening.TicketsBought);
        }

        partial void ToggleSoldOut(NSObject sender)
        {
            ToggleSoldOut();
            _checkboxSoldOut.State = ViewController.GetNSCellStateValue(_screening.SoldOut);
        }

        [Action("ToggleAttendance:")]
        internal void ToggleAttendance(NSObject sender)
        {
            string filmFan = ((NSMenuItem)sender).Title;
            ToggleAttendance(filmFan);
        }

        [Action("NavigateFilmScreening:")]
        internal void NavigateFilmScreening(NSObject sender)
        {
            var screening = ScreeningMenuDelegate.FilmScreening(((NSMenuItem)sender).Title);
            GoToScreening(screening);
        }

        [Action("TryShowFilmInfo:")]
        internal void ShowFilmInfo(NSObject sender)
        {
            TryShowFilmInfo(sender);
        }
        #endregion

        #region Events
        public EventHandler DialogAccepted;

        internal void RaiseDialogAccepted()
        {
            DialogAccepted?.Invoke(this, EventArgs.Empty);
        }

        public EventHandler DialogCanceled;

        internal void RaiseDialogCanceled()
        {
            DialogCanceled?.Invoke(this, EventArgs.Empty);
        }
        #endregion
    }
}
