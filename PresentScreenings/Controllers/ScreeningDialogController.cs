// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using System.Linq;
using Foundation;
using AppKit;
using CoreGraphics;
using System.Text;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening dialog controler, manages a dialog which displays extra information
    /// of a screening and in which editable screening properties can be changed.
    /// </summary>

    public partial class ScreeningDialogController : GoToScreeningDialog, IScreeningProvider
    {
        #region Constants
        private const float _xMargin = ControlsFactory.HorizontalMargin;
        private const float _yMargin = ControlsFactory.BigVerticalMargin;
        private const float _xBetweenLabels = ControlsFactory.HorizontalPixelsBetweenLabels;
        private const float _yBetweenViews = ControlsFactory.VerticalPixelsBetweenViews;
        private const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        private const float _labelHeight = ControlsFactory.StandardLabelHeight;
        private const float _imageButtonWidth = ControlsFactory.StandardImageButtonWidth;
        private const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        private const float _yControlsDistance = ControlsFactory.VerticalPixelsBetweenControls;
        private const float _subsectionLabelWidth = ControlsFactory.SubsectionLabelWidth;
        #endregion

        #region Private Members
        private nfloat _yCurr;
        private Screening _screening;
        private DaySchemaScreeningControl _senderControl;
        private static ViewController _presentor;
        private List<Screening> _filmScreenings;
        private FilmScreeningControl _screeningInfoControl;
        private Dictionary<string, AttendanceCheckbox> _attendanceCheckboxByFilmFan;
        private NSView _sampleSubView;
        #endregion

        #region Properties
        public static ViewController Presentor
        {
            get => _presentor;
            set => _presentor = (ViewController)value;
        }

        public bool ScreeningInfoChanged
        {
            get => CombinationWindowDelegate.ScreeningInfoChanged;
            private set
            {
                View.Window.DocumentEdited = value;
                if (value)
                {
                    CombinationWindowDelegate.ScreeningInfoChanged = true;
                }
            }
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
            Presentor.ScreeningInfoDialog = this;
            Presentor.RunningPopupsCount += 1;

            // Initialize the list of screenings.
            _filmScreenings = _screening.FilmScreenings;

            // Set window delegate.
            View.Window.Delegate = new CombinationWindowDelegate(View.Window, CloseDialog);

            // Populate the controls.
            SetControlValues();

            // Create the controls that are not defined in Xcode.
            CreateSubsectionLabel();
            CreateFilmFanControls();
            CreateScreeningsScrollView();

            // Disable Resizing.
            DisableResizing(this, _sampleSubView);
        }

        public override void ViewWillDisappear()
        {
            // Tell the presentor we're gone.
            Presentor.RunningPopupsCount--;
            if (Presentor.RunningPopupsCount == 0)
            {
                Presentor.ScreeningInfoDialog = null;
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
            Presentor.GoToScreening(screening);
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
            _filmInfoButton.Action = new ObjCRuntime.Selector("ShowFilmInfo:");

            // Select the sending screening control in the screenings table.
            _senderControl.Selected = true;

            // Populate the labels.
            PopulateTitleLabel();
            _labelScreen.StringValue = _screening.Screen.ParseName;
            _labelTime.StringValue = _screening.ToLongTimeString();
            _labelPresent.StringValue = _screening.AttendeesString();

            // Populate the checkboxes.
            _checkboxTicketsBought.Activated += (s, e) => ToggleTicketsBought();
            _checkboxTicketsBought.State = ViewController.GetNSCellStateValue(_screening.TicketsBought);
            _checkboxSoldOut.Activated += (s, e) => ToggleSoldOut();
            _checkboxSoldOut.State = ViewController.GetNSCellStateValue(_screening.SoldOut);

            // Create the Visit Website button.
            CreateVisitFilmWebsiteButton();
        }

        private void PopulateTitleLabel()
        {
            _labelTitle.StringValue = $"{_screening.FilmTitle} ({_screening.Film.MinutesString})";
            if (_screening.Extra != string.Empty)
            {
                _labelTitle.StringValue += " (+ " + _screening.Extra + ")";
            }
            _labelTitle.LineBreakMode = NSLineBreakMode.TruncatingTail;
            _labelTitle.ToolTip = TitleLableTooltip();
        }

        private string TitleLableTooltip()
        {
            var film = _screening.Film;
            var builder = new StringBuilder(film.ToString());

            // If present, add the short description.
            if (film.FilmInfo.FilmDescription != string.Empty)
            {
                builder.AppendLine();
                builder.AppendLine();
                builder.Append(film.FilmInfo.FilmDescription);
            }

            // If present, add the screened films.
            builder.Append(film.FilmInfo.ScreenedFilmsTostring());

            return builder.ToString();
        }

        private void CreateSubsectionLabel()
        {
            var frame = _labelTitle.Frame;
            var leftPosition = frame.X + frame.Width + _xBetweenLabels;
            var subsectionRect = new CGRect(leftPosition, frame.Y, _subsectionLabelWidth, frame.Height);
            var subsectionLabel = ControlsFactory.NewSubsectionLabel(subsectionRect, _screening.Film, true);
            View.AddSubview(subsectionLabel);
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

        private void CreateVisitFilmWebsiteButton()
        {
            // Set the position.
            var xCurr = _closeButton.Frame.X - _imageButtonWidth;
            var yCurr = _closeButton.Frame.Y;

            // Create the Website Button.
            var websiteButton = ControlsFactory.NewVisitWebsiteButton(xCurr, yCurr, CurrentFilm);
            websiteButton.Enabled = true;
            View.AddSubview(websiteButton);
        }

        private void HandleFilmFanRatingEditingBegan(NSComboBox comboBox, string filmFan)
        {
            _closeButton.Enabled = false;
        }

        private void HandleFilmFanRatingEditingEnded(NSComboBox comboBox, string filmFan)
        {
            int filmId = _screening.FilmId;
            Func<string, string> getControlValue = r => GetNewValueFromComboBox(comboBox, r);
            Presentor.SetRatingIfValid(comboBox, getControlValue, filmId, filmFan);
            _closeButton.Enabled = true;
            if (FilmRating.RatingChanged)
            {
                _closeButton.Title = ControlsFactory.TitleByChanged[true];
            }
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
        public void CloseDialog()
        {
            // Save changed data.
            CombinationWindowDelegate.SaveChangedData();

            // Close the dialog.
            Presentor.DismissViewController(this);
        }

        public static void SaveScreeningInfo()
        {
            // Save the screening info.
            ViewController.App.WriteScreeningInfo();
            CombinationWindowDelegate.ScreeningInfoChanged = false;
            Presentor.ScreeningInfoChanged = false;

            // Trigger a local notification.
            string title = "Screening Info Saved";
            string text = $"Screening info has been saved in {AppDelegate.DocumentsFolder}.";
            AlertRaiser.RaiseNotification(title, text);
        }

        public void PopulateDialog(DaySchemaScreeningControl sender)
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
            Presentor.UpdateAttendanceStatus(_screening, false);
            Presentor.ReloadScreeningsView();
            UpdateScreeningControls();
            _screeningInfoControl.ReDraw();
            _closeButton.Title = ControlsFactory.TitleByChanged[true];
            ScreeningInfoChanged = true;
        }

        public void UpdateMovedScreeningInfo()
        {
            _labelTime.StringValue = _screening.ToLongTimeString();
            UpdateAttendances();
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

        [Action("ShowFilmInfo:")]
        internal void ShowFilmInfo(NSObject sender)
        {
            PerformSegue("ScreeningToFilmInfo", sender);
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
