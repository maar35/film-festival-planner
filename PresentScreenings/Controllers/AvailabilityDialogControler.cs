// This file has been autogenerated from a class added in the UI designer.

using System;

using Foundation;
using AppKit;
using CoreGraphics;
using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
	/// <summary>
    /// Availability Dialog Controller, manages the user interface to
    /// administrate film fan availablility.
    /// </summary>

	public partial class AvailabilityDialogControler : NSViewController
    {
        #region Private Constants
        private const float _xMargin = ControlsFactory.HorizontalMargin;
        private const float _yMargin = ControlsFactory.BigVerticalMargin;
        private const float _labelWidth = ControlsFactory.StandardLabelWidth;
        private const float _labelHeight = ControlsFactory.StandardLabelHeight;
        private const float _controlWidth = ControlsFactory.SmallControlWidth;
        private const float _controlHeight = ControlsFactory.StandardButtonHeight;
        private const float _yControlsMargin = ControlsFactory.BigVerticalMargin;
        private const float _xBetweenControls = ControlsFactory.HorizontalPixelsBetweenControls;
        private const float _yBetweenControls = ControlsFactory.VerticalPixelsBetweenControls;
        private const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        #endregion

        #region Private Members
        private bool _availablityChanged = false;
        private float _contentWidth = 2 * _xMargin + _labelWidth + _controlWidth + _xBetweenControls;
        private float _yCurr;
        private NSButton _doneButton;
        private NSView _sampleView;
        private Dictionary<bool, string> _titleByChanged = new Dictionary<bool, string> { };
        private Dictionary<string, NSButton> _checkboxByFan = new Dictionary<string, NSButton> { };
        private Dictionary<string, Dictionary<DateTime, NSButton>> _checkboxByDayByFan = new Dictionary<string, Dictionary<DateTime, NSButton>> { };
        #endregion

        #region Properties
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        public ViewController Presentor { get; set; }
        public List<DateTime> FestivalDays => ScreeningsPlan.FestivalDays;
        public TimeSpan DayTimeSpan => new TimeSpan(1, 0, 0, 0);
        public DateTime FestivalStartTime => FestivalDays.First();
        public DateTime FestivalEndTime => FestivalDays.Last() + DayTimeSpan;
        #endregion

        #region Constructors
        public AvailabilityDialogControler(IntPtr handle) : base(handle)
        {
            _titleByChanged.Add(true, "Save");
            _titleByChanged.Add(false, "Done");
        }
        #endregion

        #region Override Methods
        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Tell the app delegate we're alive.
            App.AvailabilityDialogControler = this;

            // Initialize the presentor.
            Presentor = App.Controller;

            // Inactivate screenings view actions.
            Presentor.RunningPopupsCount++;

            // Create the controls that were not defined in Xcode.
            PopulateDialogView();

            // Set constraints of the in-code generated UI elements.
            Presentor.DisableResizing(this, _sampleView);
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate we're gone.
            App.AvailabilityDialogControler = null;

            // Tell the main view controller we're gone.
            Presentor.RunningPopupsCount--;
        }
        #endregion

        #region Public Methods
        public void CloseDialog()
        {
            if (_availablityChanged)
            {
                // Save the availabilities.
                App.WriteFilmFanAvailabilities();

                // Trigger a local notification.
                string title = "Availabilities saved";
                string text = $"Film fan availabilites have been saved in {AppDelegate.DocumentsFolder}.";
                AlertRaiser.RaiseNotification(title, text);
            }

            // Close the dialog.
            Presentor.DismissViewController(this);
        }
        #endregion

        #region Private Methods workiong wioth visual elements.
        private void PopulateDialogView()
        {
            // Adapt the window width to the number of film fans.
            AdaptWindowSize();

            // Initialize the current vertical position.
            _yCurr = (float)View.Frame.Height;

            // Create the instructions label.
            _yCurr -= _yMargin;
            CreateInstructionsLabel();

            // Create the film fan labels.
            _yCurr -= _yBetweenLabels;
            CreateFilmFanLabels();

            // Create the select/deselect all days controls.
            _yCurr -= _yBetweenLabels;
            CreateAllDaysCheckboxes();

            // Create the per day select/deselect controls.
            _yCurr -= _yBetweenControls;
            CreatePerDayCheckboxes();

            // Create the action buttons at the bottom of the screen.
            CreateActionButtons();

            // Set the states of all controls.
            UpdateControls();
        }

        private void AdaptWindowSize()
        {
            var n = ScreeningInfo.FilmFans.Count;
            var frame = View.Window.Frame;
            frame.Width = 2 * _xMargin + _labelWidth + n * (_xBetweenControls + _controlWidth);
            View.Window.SetFrame(frame, true);
        }

        private void CreateInstructionsLabel()
        {
            var labelHeight = 2 * _labelHeight + 2;
            _yCurr -= labelHeight;
            var rect = new CGRect(_xMargin, _yCurr, _contentWidth, labelHeight);
            var instructionLabel = ControlsFactory.NewStandardLabel(rect, true);
            instructionLabel.StringValue = $"Check the boxes to indicate availability for the {AppDelegate.Festival} {AppDelegate.FestivalYear} festival days";
            instructionLabel.LineBreakMode = NSLineBreakMode.ByWordWrapping;
            View.AddSubview(instructionLabel);
        }

        private void CreateFilmFanLabels()
        {
            _yCurr -= _labelHeight;
            var xCurr = _xMargin + _labelWidth + _xBetweenControls;
            var rect = new CGRect(xCurr, _yCurr, _labelWidth, _labelHeight);
            foreach (var fan in ScreeningInfo.FilmFans)
            {
                var fanLabel = ControlsFactory.NewStandardLabel(rect, true);
                fanLabel.StringValue = fan;
                fanLabel.Font = NSFont.BoldSystemFontOfSize(NSFont.SystemFontSize);
                View.AddSubview(fanLabel);
                xCurr += _controlWidth + _xBetweenControls;
                rect.X = xCurr;
            }
        }

        private void CreateAllDaysCheckboxes()
        {
            _yCurr -= _labelHeight;

            // Create a label indicating that the checkboxes in this row apply
            // to all festival days.
            var labelRect = new CGRect(_xMargin, _yCurr, _labelWidth, _labelHeight);
            var label = ControlsFactory.NewStandardLabel(labelRect, true);
            label.StringValue = $"All {FestivalDays.Count} days";
            View.AddSubview(label);

            // Create a checkbox for each film fan.
            var xBox = _xMargin + _labelWidth + _xBetweenControls;
            var boxAnchor = new CGPoint(xBox, _yCurr);
            CreateFilmFanCheckboxes(View, boxAnchor, FestivalDays);
        }

        private void CreatePerDayCheckboxes()
        {
            // Create the document view.
            var n = FestivalDays.Count;
            var documentWidth = View.Frame.Width - 2 * _xMargin;
            var documentHeight = n * _labelHeight + (n-1) * _yBetweenLabels;
            var documentFrame = new CGRect(0, 0, documentWidth, documentHeight);
            var documentView = new NSView(documentFrame);

            // Create the scroll view.
            var scrollerHeight = _yCurr - _yControlsMargin - _controlHeight - _yBetweenControls;
            _yCurr -= scrollerHeight;
            var scrollerFrame = new CGRect(_xMargin, _yCurr, documentWidth, scrollerHeight);
            var scrollerView = ControlsFactory.NewStandardScrollView(scrollerFrame, documentView, true);
            View.AddSubview(scrollerView);

            // Populate the document view.
            var yCurr = documentView.Frame.Height - _labelHeight;
            var labelRect = new CGRect(0, yCurr, _labelWidth, _labelHeight);
            foreach (var day in FestivalDays)
            {
                // Create the day label.
                var label = ControlsFactory.NewStandardLabel(labelRect, true);
                label.StringValue = Screening.LongDayString(day);
                documentView.AddSubview(label);

                // Create the film fan checkboxes.
                var xCurr = _labelWidth + _xBetweenControls;
                var daySingleton = new List<DateTime> { day };
                CreateFilmFanCheckboxes(documentView, new CGPoint(xCurr, yCurr), daySingleton);

                // Update the vertical position.
                yCurr -= _labelHeight + _yBetweenLabels;
                labelRect.Y = yCurr;
            }

            // Set sample view used to disable resizing.
            _sampleView = scrollerView;
        }

        private void CreateFilmFanCheckboxes(NSView view, CGPoint boxAnchor, List<DateTime> days)
        {
            // Initialize the model rectangle.
            var boxRect = new CGRect(boxAnchor.X, boxAnchor.Y, _controlWidth, _labelHeight);

            foreach (var fan in ScreeningInfo.FilmFans)
            {
                // Populate the checkbox.
                var box = ControlsFactory.NewCheckbox(boxRect);
                box.Title = string.Empty;
                box.Activated += (s, e) => SetAvailability(s, fan, days);
                box.AllowsMixedState = true;
                view.AddSubview(box);

                // Update the controls dictionary.
                StoreControlDictionaries(box, fan, days);

                // Update the horizontal position.
                boxRect.X += _controlWidth + _xBetweenControls;
            }
        }

        private void CreateActionButtons()
        {
            var xCurr = View.Frame.Width;

            // Create the Close button.
            xCurr -= _xBetweenControls + _controlWidth;
            var rect = new CGRect(xCurr, _yControlsMargin, _controlWidth, _controlHeight);
            _doneButton = ControlsFactory.NewCancelButton(rect);
            _doneButton.Action = new ObjCRuntime.Selector("CloseAvailabilityDialog:");
            View.AddSubview(_doneButton);
        }
        #endregion

        #region Private Methods working with UI Logic.
        private void SetAvailability(object sender, string fan, List<DateTime> days)
        {
            var state = ((NSButton)sender).State;
            foreach (var day in days)
            {
                SetAvailability(state, fan, day);
            }
            _availablityChanged = true;
            UpdateControls(fan, true);
        }

        private void SetAvailability(NSCellStateValue state, string fan, DateTime day)
        {
            DeleteAvailability(fan, day);
            if (state != NSCellStateValue.Off)
            {
                var availability = new FilmFanAvailability(fan, StartTime(day), EndTime(day));
                ScreeningsPlan.Availabilities.Add(availability);
            }
        }

        private void DeleteAvailability(string fan, DateTime day)
        {
            // Find the availablity of this film fan on the given day.
            var fanAvailabilities = (
                from FilmFanAvailability availability in ScreeningsPlan.Availabilities
                where availability.Equals(fan, day)
                select availability
            ).ToList();

            // Remove the availabilities of this film fan on the given day.
            foreach (var availability in fanAvailabilities)
            {
                ScreeningsPlan.Availabilities.Remove(availability);
            }
        }

        private DateTime StartTime(DateTime day)
        {
            return day;
        }

        private DateTime EndTime(DateTime day)
        {
            return day + DayTimeSpan;
        }

        private void StoreControlDictionaries(NSButton box, string fan, List<DateTime> days)
        {
            // Establish which controls dictionary is applicable.
            bool usePerDayDict = days.Count == 1;

            // Update the controls dictionary.
            if (usePerDayDict)
            {
                if (!_checkboxByDayByFan.ContainsKey(fan))
                {
                    _checkboxByDayByFan.Add(fan, new Dictionary<DateTime, NSButton> { });
                }
                foreach (var day in days)
                {
                    _checkboxByDayByFan[fan].Add(day, box);
                }
            }
            else
            {
                _checkboxByFan.Add(fan, box);
            }
        }

        private void UpdateControls()
        {
            // Update the title of the Done/Save button.
            _doneButton.Title = _titleByChanged[_availablityChanged];

            // Update the states of the checkboxes.
            foreach (var fan in ScreeningInfo.FilmFans)
            {
                UpdateControls(fan);
            }
        }

        private void UpdateControls(string fan, bool includeDoneButton = false)
        {
            // Update the title of the Done/Save button if indicated.
            if (includeDoneButton)
            {
                _doneButton.Title = _titleByChanged[_availablityChanged];
            }

            // Update the All Days checkbox of this film fan.
            var allDaysBox = _checkboxByFan[fan];
            allDaysBox.State = AvailabilityState(fan);

            // Update the Per Day checkboxes.
            foreach (var boxByDay in _checkboxByDayByFan[fan])
            {
                DateTime day = boxByDay.Key;
                NSButton box = boxByDay.Value;
                box.State = AvailabilityState(fan, day);
            }
        }

        private NSCellStateValue AvailabilityState(string fan)
        {
            // Find the availablity of this film fan.
            var fanAvailabilities = (
                from FilmFanAvailability availability in ScreeningsPlan.Availabilities
                where availability.FilmFan == fan
                select availability
            ).ToList();

            // Return "Off" in case of no availability.
            if (fanAvailabilities.Count == 0)
            {
                return NSCellStateValue.Off;
            }

            // Establish whether this fan is available on all days of the festival.
            bool availableAllDays = fanAvailabilities.Count() == FestivalDays.Count;

            // Return the corresponding cell state.
            return availableAllDays ? NSCellStateValue.On : NSCellStateValue.Mixed;
        }

        private NSCellStateValue AvailabilityState(string fan, DateTime day)
        {
            // Find the availability of this film fan on the given day.
            var fanAvailabilities = (
                from FilmFanAvailability availability in ScreeningsPlan.Availabilities
                where availability.Equals(fan, day)
                select availability
            ).ToList();

            // Return the associated cell state.
            return fanAvailabilities.Count == 0 ? NSCellStateValue.Off : NSCellStateValue.On;
        }
        #endregion

        #region Custom Actions
        [Action("CloseAvailabilityDialog:")]
        private void ClosePlanView(NSObject sender)
        {
            CloseDialog();
        }
        #endregion
    }
}
