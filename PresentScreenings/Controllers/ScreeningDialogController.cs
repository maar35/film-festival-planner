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
        const float _buttonWidth = ControlsFactory.StandardButtonWidth;
        const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        const float _yControlsDistance = ControlsFactory.VerticalPixelsBetweenControls;
        #endregion

        #region Private Members
        nfloat _yCurr;
        Screening _screening;
        ScreeningControl _control;
        ViewController _presentor;
        List<Screening> _filmScreenings;
        FilmScreeningControl _screeningInfoControl;
        Dictionary<string, AttendanceCheckbox> _attendanceCheckboxByFriend;
        #endregion

        #region Computed Properties
        public ViewController Presentor
        {
            get => _presentor;
            set => _presentor = (ViewController)value;
        }
        #endregion

        #region Interface Implementation Properties
        public Screening CurrentScreening => Presentor.Plan.CurrScreening;
        public List<Screening> Screenings => ViewController.FilmScreenings(Presentor.Plan.CurrScreening.FilmId);
        public Film CurrentFilm => ViewController.GetFilmById(CurrentScreening.FilmId);
        #endregion

        #region Constructors
        public ScreeningDialogController(IntPtr handle) : base(handle)
        {
            _filmScreenings = new List<Screening> { };
            _attendanceCheckboxByFriend = new Dictionary<string, AttendanceCheckbox> { };
        }
        #endregion

        #region Override Methods
        public override void AwakeFromNib()
        {
            base.AwakeFromNib();
        }
        public override void ViewDidLoad()
        {
            // Tell the presentor we're alive.
            _presentor.RunningPopupsCount += 1;

            // Populate controls.
            _filmInfoButton.Action = new ObjCRuntime.Selector("ShowFilmInfo:");
        }

        public override void ViewWillAppear()
        {
            base.ViewWillAppear();
            _control.Selected = true;
            _filmScreenings = _presentor.FilmScreenings(_screening);
            _checkboxTicketsBought.Activated += (s, e) => ToggleTicketsBought();
            _checkboxSoldOut.Activated += (s, e) => ToggleSoldOut();
            _checkboxIAttend.Activated += (s, e) => ToggleMyAttandance();
            SetControlValues();
            CreateFriendControls();
            CreateScreeningsScrollView();
        }

        public override void ViewWillDisappear()
        {
            _presentor.RunningPopupsCount--;
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
                    filmInfoModal.ShowScreenings = false;
                    break;
            }
        }
        #endregion

        #region Private Methods
        void SetControlValues()
        {
            _labelTitle.StringValue = _screening.FilmTitle;
            _labelScreen.StringValue = _screening.Screen.ParseName;
            _labelTime.StringValue = _screening.ToLongTimeString();
            _labelPresent.StringValue = _screening.AttendeesString();
            MyAttendanceTitler.SetTitle((TitledButton)_buttonIAttend, _screening.IAttend);
            _checkboxTicketsBought.State = ViewController.GetNSCellStateValue(_screening.TicketsBought);
            _checkboxSoldOut.State = ViewController.GetNSCellStateValue(_screening.SoldOut);
            _checkboxIAttend.Title = ScreeningStatus.Me;
            _checkboxIAttend.State = AttendanceCheckbox.SetAttendanceState(_screening.IAttend);
        }

        void CreateFriendControls()
        {
            // Clone the Rating combo box.
            var comboBoxFrame = _comboboxRating.Frame;
            var comboBoxFont = _comboboxRating.Font;
            var myRatingComboBox = ControlsFactory.NewRatingComboBox(comboBoxFrame, comboBoxFont);
            myRatingComboBox.EditingEnded += (s, e) => HandleMyRatingEditingEnded(myRatingComboBox);
            myRatingComboBox.StringValue = _screening.Rating.ToString();
            View.AddSubview(myRatingComboBox);

            // Dispose the original Rating combo box.
            _comboboxRating.RemoveFromSuperview();
            _comboboxRating.Dispose();

            // Initialize the vertical postion of run-time created controls.
            _yCurr = comboBoxFrame.Y;

            // Initialze values to construct the Friend Attendance checkboxes.
            var checkBoxFrame = _checkboxIAttend.Frame;
            var checkBoxShift = comboBoxFrame.Y - checkBoxFrame.Y;

            foreach (var friend in ScreeningStatus.MyFriends)
            {
                // Update the vertical position.
                _yCurr -= myRatingComboBox.Frame.Height + _yControlsDistance;

                // Create the Rriend Rating combobox.
                comboBoxFrame.Y = _yCurr;
                var friendRatingComboBox = ControlsFactory.NewRatingComboBox(comboBoxFrame, comboBoxFont);
                friendRatingComboBox.EditingEnded += (s, e) => HandleFriendRatingEditingEnded(friendRatingComboBox, friend);
                friendRatingComboBox.StringValue = _presentor.GetFriendFilmRating(_screening.FilmId, friend).ToString();
                View.AddSubview(friendRatingComboBox);

                // Create the Friend Attendance checkbox.
                checkBoxFrame.Y = _yCurr - checkBoxShift;
                var friendCheckbox = new AttendanceCheckbox(checkBoxFrame);
                friendCheckbox.Title = friend;
                friendCheckbox.State = AttendanceCheckbox.SetAttendanceState(_screening.FriendAttends(friend));
                friendCheckbox.Activated += (s, e) => ToggleFriendAttendance(friend);
                View.AddSubview(friendCheckbox);

                // Link the checkbox to the friend.
                _attendanceCheckboxByFriend.Add(friend, friendCheckbox);
            }
        }

        void CreateScreeningsScrollView()
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
            var scrollView = ControlsFactory.NewStandardScrollView(scrollViewFrame, screeningsView);
            View.AddSubview(scrollView);

            // Display the screenings.
            GoToScreeningDialog.DisplayScreeningControls(screenings, screeningsView, GoToScreening, ref _screeningInfoControl);

            // Scroll to the selected screening.
            GoToScreeningDialog.ScrollScreeningToVisible(CurrentScreening, scrollView);

        }

        void UpdateAttendances()
        {
            _labelPresent.StringValue = _screening.AttendeesString();
            _presentor.UpdateAttendanceStatus(_screening);
            _presentor.ReloadScreeningsView();
            GoToScreeningDialog.UpdateScreeningControls();
            _screeningInfoControl.ReDraw();
        }

        public override void GoToScreening(Screening screening)
        {
            _presentor.GoToScreening(screening);
            CloseDialog();
        }

        void CloseDialog()
        {
            _presentor.DismissViewController(this);
        }

        void HandleMyRatingEditingEnded(NSComboBox comboBox)
        {
            FilmRating rating = _screening.Rating;
            string oldRatingString = rating.Value;
            string newRatingString = rating.Value;
            if (SetNewValueFromComboBox(comboBox, ref newRatingString))
            {
                if (_screening.Rating.SetRating(newRatingString))
                {
                    _presentor.ReloadScreeningsView();
                }
                else
                {
                    comboBox.StringValue = oldRatingString;
                }
            }
        }

        void HandleFriendRatingEditingEnded(NSComboBox comboBox, string friend)
        {
            int filmId = _screening.FilmId;
            FilmRating rating = _presentor.GetFriendFilmRating(filmId, friend);
            string oldRatingString = rating.Value;
            string newRatingString = rating.Value;
            if (SetNewValueFromComboBox(comboBox, ref newRatingString))
            {
                if (rating.SetRating(newRatingString))
                {
                    _presentor.SetFriendFilmRating(filmId, friend, rating);
                    _presentor.ReloadScreeningsView();
                }
                else
                {
                    comboBox.StringValue = oldRatingString;
                }
            }
        }

        bool SetNewValueFromComboBox(NSComboBox comboBox, ref string refString)
        {
            string comboBoxString = comboBox.StringValue;
            if (comboBox.SelectedValue == null)
            {
                bool found = false;
                var max = comboBox.Count;
                for (int i = 0; i < max; i++)
                {
                    if (comboBoxString == comboBox.Values[i].ToString())
                    {
                        found = true;
                        break;
                    }
                }
                if (!found)
                {
                    comboBox.StringValue = refString;
                    return false;
                }
            }
            else
            {
                comboBoxString = comboBox.SelectedValue.ToString();
            }
            if (comboBoxString == refString)
            {
                return false;
            }
            refString = comboBoxString;
            return true;
        }
        #endregion

        #region Public Methods
        public void PopulateDialog(ScreeningControl sender)
        {
            _control = sender;
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

        public void ToggleMyAttandance()
        {
            _screening.ToggleMyAttendance();
            MyAttendanceTitler.SetTitle((TitledButton)_buttonIAttend, _screening.IAttend);
            UpdateAttendances();
        }

        public void ToggleFriendAttendance(string friend)
        {
            _screening.ToggleFriendAttendance(friend);
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

        partial void IAttendScreening(NSObject sender)
        {
            RaiseAttendanceChanged();
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

        [Action("ToggleMyAttandance:")]
        void ToggleMyAttandance(NSObject sender)
        {
            ToggleMyAttandance();
            _checkboxIAttend.State = AttendanceCheckbox.SetAttendanceState(_screening.IAttend);
        }

        [Action("ToggleFriendAttendance:")]
        void ToggleFriendAttendance(NSObject sender)
        {
            string friend = ((NSMenuItem)sender).Title;
            ToggleFriendAttendance(friend);
            _attendanceCheckboxByFriend[friend].State = AttendanceCheckbox.SetAttendanceState(_screening.FriendAttends(friend));
        }

        [Action("NavigateFilmScreening:")]
        internal void NavigateFilmScreening(NSObject sender)
        {
            var screening = ScreeningMenuDelegate.FilmScreening(((NSMenuItem)sender).Title);
            GoToScreening(screening);
        }

        [Action("ShowFilmInfo:")]
        private void ShowFilmInfo(NSObject sender)
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

        public EventHandler AttendanceChanged;

        internal void RaiseAttendanceChanged()
        {
            AttendanceChanged?.Invoke(this, EventArgs.Empty);
        }
        #endregion
    }
}
