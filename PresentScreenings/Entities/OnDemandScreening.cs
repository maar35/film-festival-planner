using System;

namespace PresentScreenings.TableView
{
    public class OnDemandScreening : Screening
    {
        #region Private Variables
        private const string _expireTimeFormat = "ddd d-M HH:mm";
        private TimeSpan _duration;
        #endregion

        #region Properties
        public DateTime WindowStartTime { get; }
        public DateTime WindowEndTime { get; }
        public Screen DisplayScreen { get; set; }
        #endregion

        #region Calculated Properties
        public TimeSpan BounceSpan => new TimeSpan(8, 59, 0);
        public TimeSpan MarginSpan => new TimeSpan(0, 1, 0);
        #endregion

        #region Constructors
        public OnDemandScreening(string screeningText) : base(screeningText)
        {
            // Parse the relevant part of the input string.
            string[] fields = screeningText.Split(';');
            WindowStartTime = DateTime.Parse(fields[2]);
            WindowEndTime = DateTime.Parse(fields[3]);

            // Assign other properties.
            EndTime = StartTime + Film.Duration;
            _duration = EndTime - StartTime;
            DisplayScreen = Screen;
        }
        #endregion

        #region Override Methods
        public override string ToFilmScreeningLabelString()
        {
            return $"{DayString(WindowStartTime)} {Screen} {WindowStartTime.ToString(_dtFormat)}-{WindowEndTime.ToString(_dtFormat)} {ExtraTimeSymbolsString()} {ShortAttendingFriendsString()}{ScreeningTitleIfDifferent()}";
        }

        protected override string AvailableTillString()
        {
            return $"{WindowEndTime.ToString(_expireTimeFormat)}";
        }
        #endregion

        #region Public Methods
        public void SetStartTime(DateTime time)
        {
            // Remember if move was forward or backward.
            bool movedForward = time > StartTime;

            // Set the new screening times.
            StartTime = time;
            EndTime = StartTime + _duration;

            // Keep the screening on the board.
            if (StartTime.TimeOfDay < BounceSpan)
            {
                if (movedForward)
                {
                    StartTime -= StartTime.TimeOfDay + MarginSpan;
                }
                else
                {
                    StartTime += BounceSpan - StartTime.TimeOfDay + MarginSpan;
                }
                EndTime = StartTime + _duration;
            }

            // Maintain the min/max window.
            if (StartTime < WindowStartTime)
            {
                StartTime = WindowStartTime;
                EndTime = StartTime + _duration;
            }
            if (EndTime > WindowEndTime)
            {
                EndTime = WindowEndTime;
                StartTime = EndTime - _duration;
            }
        }

        public void MoveStartTime(TimeSpan span)
        {
            SetStartTime(StartTime + span);
        }

        public void SetEndTime(Screening screening)
        {
            if (EndTime == StartTime)
            {
                _duration = screening.Duration;
                EndTime = StartTime + _duration;
            }
        }
        #endregion
    }
}
