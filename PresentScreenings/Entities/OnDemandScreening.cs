using System;

namespace PresentScreenings.TableView
{
    public class OnDemandScreening : Screening
    {
        #region Properties
        public DateTime WindowStartTime { get; }
        public DateTime WindowEndTime { get; }
        public Screen DisplayScreen { get; set; }
        #endregion

        #region Calculated Properties

        #endregion

        #region Constructors
        public OnDemandScreening(string screeningText) : base(screeningText)
        {
            WindowStartTime = base.StartTime;
            WindowEndTime = base.EndTime;
            EndTime = StartTime + Film.Duration;
            DisplayScreen = Screen;
        }
        #endregion

        #region Override Methods
        public override string ToFilmScreeningLabelString()
        {
            return $"{DayString(StartTime)} {Screen} {StartTime.ToString(_dtFormat)}-{EndTime.ToString(_dtFormat)} {ExtraTimeSymbolsString()} {ShortAttendingFriendsString()}{ScreeningTitleIfDifferent()}";
        }
        #endregion

        #region Public Methods
        public void SetEndTime(Screening screening)
        {
            if (EndTime == StartTime)
            {
                EndTime = StartTime + screening.Duration;
            }
        }
        #endregion
    }
}
