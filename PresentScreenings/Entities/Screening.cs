﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using static PresentScreenings.TableView.FilmInfo;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Represents the data that defines a screening, enriched with related
    /// information like attendance, availability of tickets and whether another
    /// screening is attended at the same time or the film is already planned.
    /// </summary>

    public class Screening : ListStreamer, IComparable
    {
        #region Constant Private Members
        protected const string _dateFormat = "yyyy-MM-dd";
        protected const string _timeFormat = "HH:mm";
        protected const string _dtFormat = "ddd dd-MM HH:mm";
        protected const string _dayOfWeekFormat = "dddd d MMMM";
        protected const string _durationFormat = "hh\\:mm";
        #endregion

        #region Private Members
        protected string _newLine = Environment.NewLine;
        protected ScreeningInfo _screeningInfo;
        #endregion

        #region Properties
        public int OriginalFilmId { get; }
        public Screen Screen { get; }
        public int? CombinationProgramId { get; }
        public string Subtitles { get; }
        public string QAndA { get; }
        public string Extra { get; }
        #endregion

        #region Calculated Properties
        public int FilmId { get => _screeningInfo.CombinedFilmId; set => _screeningInfo.CombinedFilmId = value; }
        public Film Film { get => ViewController.GetFilmById(FilmId); set => FilmId = value.FilmId; }
        public string FilmTitle => Film.Title;
        public string ScreeningTitle => ViewController.GetFilmById(OriginalFilmId).Title;
        public string CoincideKey => GetCoincideKey();
        public Screen DisplayScreen { get => GetDisplayScreen(); set => SetDisplayScreen(value); }
        public DateTime StartTime { get => _screeningInfo.MovableStartTime; protected set => _screeningInfo.MovableStartTime = value; }
        public DateTime EndTime { get => _screeningInfo.MovableEndTime; protected set => _screeningInfo.MovableEndTime = value; }
        public DateTime StartDate => StartTime.Date;
        public TimeSpan Duration => EndTime - StartTime;
        public FilmRating Rating => Film.Rating;
        public FilmRating SecondRating => Film.SecondRating;
        public bool HasQAndA => QAndA != string.Empty;
        public List<string> AttendingFilmFans { get => _screeningInfo.Attendees; set => _screeningInfo.Attendees = value; }
        public bool IAttend => _screeningInfo.IAttend;
        public List<string> AttendingFriends => _screeningInfo.AttendingFriends;
        public bool SoldOut { get => _screeningInfo.SoldOut; set => _screeningInfo.SoldOut = value; }
        public bool TicketsBought { get => _screeningInfo.TicketsBought; set => _screeningInfo.TicketsBought = value; }
        public bool HasTimeOverlap => ViewController.OverlappingAttendedScreenings(this).Any();
        public bool HasNoTravelTime => ViewController.OverlappingAttendedScreenings(this, true).Any();
        public bool FitsAvailability => ViewController.ScreeningFitsAvailability(this);
        private Screen.ScreenType ScreenType => Screen.Type;
        public bool OnLine => ScreenType == Screen.ScreenType.OnLine;
        public bool OnDemand => ScreenType == Screen.ScreenType.OnDemand;
        public bool Location => ScreenType == Screen.ScreenType.Location;
        public int TimesIAttendFilm => ScreeningsPlan.Screenings.Count(s => s.FilmId == FilmId && s.IAttend);
        public bool IsPlannable => GetIsPlannable();
        public bool HasEligibleTheater => GetHasEligibleTheater();
        public List<Screening> FilmScreenings => ViewController.FilmScreenings(FilmId);
        public int FilmScreeningCount => FilmScreenings.Count;
        public List<ScreenedFilm> ScreenedFilms => Film.FilmInfo.ScreenedFilms;
        public int FilmsInScreening => ScreenedFilms.Count > 0 ? ScreenedFilms.Count : 1;
        public bool AutomaticallyPlanned { get => _screeningInfo.AutomaticallyPlanned; set => _screeningInfo.AutomaticallyPlanned = value; }
        public ScreeningInfo.TicketsStatus TicketStatus => ScreeningInfo.GetTicketStatus(IAttend, TicketsBought);
        public ScreeningInfo.ScreeningStatus Status { get => _screeningInfo.Status; set => _screeningInfo.Status = value; }
        public ScreeningInfo.Warning Warning { get; set; } = ScreeningInfo.Warning.NoWarning;
        public List<IFilmOutlinable> FilmOutlinables { get; private set; } = new List<IFilmOutlinable> { };
        #endregion

        #region Static Properties
        public static Action<Screening> GoToScreening { get; set; }
        public static TimeSpan WalkTimeSameTheater { get; set; }
        public static TimeSpan TravelTimeOtherTheater { get; set; }
        public static bool InOutliningOverlaps { get; set; } = false;
        public static Dictionary<string, int> IndexByName { get; }
        #endregion

        #region Constructors
        static Screening()
        {
            // Initialize the Index by Name dictionary.
            IndexByName = new Dictionary<string, int> { };
            int n = 0;
            IndexByName.Add("FilmId", n);
            IndexByName.Add("ScreenId", ++n);
            IndexByName.Add("StartTime", ++n);
            IndexByName.Add("EndTime", ++n);
            IndexByName.Add("CombinationProgramId", ++n);
            IndexByName.Add("Subtitles", ++n);
            IndexByName.Add("QAndA", ++n);
            IndexByName.Add("Extra", ++n);
            IndexByName.Add("SoldOut", ++n);
        }

        public Screening() { }

        public Screening(string screeningText)
        {
            // Assign the fields of the input string.
            string[] fields = screeningText.Split(';');
            int filmId = int.Parse(fields[IndexByName["FilmId"]]);
            int screenId = int.Parse(fields[IndexByName["ScreenId"]]);
            string startTimeString = fields[IndexByName["StartTime"]];
            string endTimeString = fields[IndexByName["EndTime"]];
            string combinationIdStr = fields[IndexByName["CombinationProgramId"]];
            string subtitles = fields[IndexByName["Subtitles"]];
            string qAndA = fields[IndexByName["QAndA"]];
            string extra = fields[IndexByName["Extra"]];
            string soldOut = fields[IndexByName["SoldOut"]];

            // Assign key properties.
            OriginalFilmId = filmId;
            Screen = ViewController.GetScreenById(screenId);
            DateTime startTime = DateTime.Parse(startTimeString);
            DateTime endTime = DateTime.Parse(endTimeString);

            // Get screening info.
            var screeningInfos = ScreeningsPlan
                .ScreeningInfos
                .Where(s => s.OriginalFilmId == OriginalFilmId && s.Screen == Screen && s.StartTime == startTime)
                .ToList();
            if (screeningInfos.Count == 0)
            {
                _screeningInfo = new ScreeningInfo(OriginalFilmId, Screen, startTime);
                StartTime = startTime;
                EndTime = endTime;
                ScreeningsPlan.ScreeningInfos.Add(_screeningInfo);
            }
            else
            {
                _screeningInfo = screeningInfos.First();
            }

            // Assign other properties.
            var filmList = ScreeningsPlan
                .Films
                .Where(f => f.FilmId == FilmId)
                .ToList();
            if (filmList.Count == 0)
            {
                string messageText = "No film found for screening";
                string informativeText = $"Can't find film with ID={FilmId} "
                    + $"while reading {AppDelegate.ScreeningsFile}."
                    + _newLine
                    + _newLine
                    + "For developers: If this is caused by a URL change of the film, please "
                    + "replace the filmId in ratings.csv, screenings.csv (two columns) and screeninginfo.";
                AlertRaiser.QuitWithAlert(messageText, informativeText);
            }
            Film = filmList.First();
            CombinationProgramId = int.TryParse(combinationIdStr, out int outcome) ? (int?)outcome : null;
            Subtitles = subtitles;
            QAndA = qAndA;
            Extra = extra;
            if (soldOut.Length > 0)
            {
                SoldOut = bool.Parse(soldOut);
            }
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return $"{ScreeningTitle}"
                + _newLine
                + $"{DayString(StartTime)} {FromTillString()} {Screen} {DurationString()} {Rating}";
        }

        public override bool ListFileIsMandatory()
        {
            // Even if FilmRatingDialogController.OnlyFilmsWithScreenings is set
            // to false, we do need at least one screening to fill the day plan.
            return true;
        }

        public override string WriteHeader()
        {
            string headerFmt = "weekday;date;{0};screen;starttime;endtime;vod till;title;duration;rating;filmsinscreening;extra;qanda;subtitles;genre;url;mainfilmdescription";
            return string.Format(headerFmt, ScreeningInfo.FilmFansString().Replace(',', ';'));
        }

        public override List<T> ReadListFromFile<T>(string fileName, Func<string, T> lineConstructor)
        {
            var screenings = base.ReadListFromFile(fileName, lineConstructor);
            if (screenings.Count() == 0)
            {
                string informativeText = $"We really need screenings, but {fileName} is empty.";
                AlertRaiser.QuitWithAlert("Data Error", informativeText);
            }
            return screenings;
        }

        public override string Serialize()
        {
            FilmInfo filmInfo = Film.FilmInfo;
            List<string> fields = new List<string> { };

            fields.Add(StartTime.DayOfWeek.ToString().Remove(3));
            fields.Add(StartTime.ToString(_dateFormat));
            foreach (var filmFan in ScreeningInfo.FilmFans)
            {
                fields.Add(ScreeningInfo.BoolToString[FilmFanAttends(filmFan)]);
            }
            fields.Add(Screen.ToString());
            fields.Add(StartTime.ToString(_timeFormat));
            fields.Add(EndTime.ToString(_timeFormat));
            fields.Add(AvailableTillString());
            fields.Add($"{Film}");
            fields.Add($"{Film.MinutesString}");
            fields.Add(ShortFriendsString(true));
            fields.Add(FilmsInScreening.ToString());
            fields.Add(Extra);
            fields.Add(QAndA);
            fields.Add(Subtitles);
            fields.Add(filmInfo.GetGenreDescription());
            fields.Add(filmInfo.Url);
            fields.Add(filmInfo.FilmDescription.Replace('\n', ' '));

            return string.Join(";", fields);
        }
        #endregion

        #region Virtual Methods
        protected virtual Screen GetDisplayScreen()
        {
            return Screen;
        }

        protected virtual void SetDisplayScreen(Screen screen)
        {
            throw new AccessViolationException("Display screen of an on-location screening can't be changed.");
        }

        protected virtual string AvailableTillString()
        {
            return string.Empty;
        }

        public virtual string ToFilmScreeningLabelString(int? filmId=null)
        {
            return string.Format("{0} {1}{2}", ToMenuItemString(), ShortAttendingFriendsString(), ScreeningTitleIfDifferent(filmId));
        }

        protected virtual bool GetIsPlannable()
        {
            bool plannable = FitsAvailability
                && TimesIAttendFilm == 0
                && !HasNoTravelTime
                && !SoldOut
                && (AppDelegate.VisitPhysical || !Location);
            return plannable;
        }

        protected virtual bool GetHasEligibleTheater()
        {
            Theater.PriorityValue priority = Screen.Theater.Priority;
            return priority == Theater.PriorityValue.High;
        }
        #endregion

        #region Interface Implementations
        public int CompareTo(object obj)
        {
            return StartTime.CompareTo(((Screening)obj).StartTime);
        }
        #endregion

        #region Public Methods
        public bool FilmFanAttends(string filmFan)
        {
            return AttendingFilmFans.Contains(filmFan);
        }

        public void ToggleFilmFanAttendance(string filmFan)
        {
            if (AttendingFilmFans.Contains(filmFan))
            {
                AttendingFilmFans.Remove(filmFan);
            }
            else
            {
                AttendingFilmFans.Add(filmFan);
                int Key(string fan) => ScreeningInfo.FilmFans.IndexOf(fan);
                AttendingFilmFans.Sort((fan1, fan2) => Key(fan1).CompareTo(Key(fan2)));
            }
        }

        public bool Overlaps(Screening otherScreening, bool useTravelTime = false)
        {
            var travelTime = useTravelTime ? GetTravelTime(otherScreening) : TimeSpan.Zero;
            return otherScreening.StartTime <= EndTime + travelTime
                && otherScreening.EndTime >= StartTime - travelTime;
        }

        public TimeSpan GetTravelTime(Screening otherScreening)
        {
            var sameTheater = Screen.Theater.TheaterId == otherScreening.Screen.Theater.TheaterId;
            var travelTime = sameTheater ? WalkTimeSameTheater : TravelTimeOtherTheater;
            return travelTime;
        }
        #endregion

        #region Public Display Methods
        public static string DayString(DateTime date)
        {
            return $"{date.DayOfWeek.ToString().Remove(3)}{date.Day}";
        }

        public static string DateTimeString(DateTime dateTime)
        {
            return $"{DayString(dateTime)} {dateTime.ToString(_timeFormat)}";
        }

        public static string LongDayString(DateTime date)
        {
            return $"{date.DayOfWeek.ToString().Remove(3)} {date.ToString(_dateFormat)}";
        }

        public string ToLongTimeString()
        {
            return $"{StartDate.ToString(_dayOfWeekFormat)} {FromTillString()} ({DurationString()}){AppendingExtraTimesString()}";
        }

        public string ToMenuItemString()
        {
            return $"{DayString(StartTime)} {DisplayScreen} {StartTime.ToString(_timeFormat)} {ExtraTimeSymbolsString()}";
        }

        public string ToScreeningLabelString(bool withDay = false)
        {
            return $"{ScreeningTitle}{_newLine}{ScreeningStringForLabel(withDay)}";
        }

        public string ToPlannedScreeningString()
        {
            return $"{ToLongTimeString()} {Screen} {ScreeningTitle}";
        }

        public string ToToolTipString()
        {
            return $"{ScreeningTitle}{_newLine}{DateTimeString(StartTime)}{_newLine}{Screen}";
        }

        public string ToConsideredScreeningString(string filmFan)
        {
            string overlaps = HasNoTravelTime ? "T!" : string.Empty;
            string available = FitsAvailability ? string.Empty : "A!";
            string filmFanAttends = AttendingFilmFans.Contains(filmFan) ? filmFan.Remove(1) : string.Empty;
            return string.Format($"{Film} {FilmScreeningCount} {Screen} {ToLongTimeString()} "
                + $"{overlaps}{available} {filmFanAttends} {ShortFriendsString()}");
        }

        public string DurationString()
        {
            return Duration.ToString(_durationFormat);
        }

        public string AppendingExtraTimesString()
        {
            string extrasString = ExtraTimeSymbolsString();
            return extrasString == string.Empty ? extrasString : $" ({Film.DurationString} + {extrasString})";
        }

        public string ExtraTimeSymbolsString()
        {
            string extrasString = (Extra == string.Empty ? Extra : "V") + (HasQAndA ? "Q" : string.Empty);
            if (extrasString != string.Empty)
            {
                extrasString = extrasString + " ";
            }
            return extrasString;
        }

        public string AttendeesString()
        {
            return string.Join(", ", AttendingFilmFans);
        }

        public string ScreeningStringForLabel(bool withDay = false)
        {
            string dayString = withDay ? $"{DayString(StartTime)} " : string.Empty;
            return $"{ExtraTimeSymbolsString()}{dayString}{Screen} {FromTillString()} {Rating} {ShortFriendsString()}";
        }

        /// <summary>
        /// Returns a string consisting of the initials of attending friends to
        /// be displayd on labels of screenings of the same film.
        /// Does not display all film fans because 'my attendance' follows from
        /// the label color.
        /// </summary>
        /// <returns></returns>
        public string ShortAttendingFriendsString()
        {
            StringBuilder abbreviationBuilder = new StringBuilder();
            foreach (var friend in AttendingFriends)
            {
                abbreviationBuilder.Append(friend.Remove(1));
            }
            return abbreviationBuilder.ToString();
        }

        /// <summary>
        /// Returns a string consisting of the initials of friends who attend
        /// the screening or have rated the screening's film.
        /// Ratings appear directly after the initial of the friend who rated.
        /// Attending friends' initials are in upper case, initials of friends
        /// who rated the film but do not attend the screening in lower case.
        /// Does not display all film fans because 'my attendance' follows from
        /// the label color.
        /// 'Me' can be included through an optional argument though.
        /// </summary>
        /// <returns></returns>
        public string ShortFriendsString(bool includeMe = false)
        {
            var screeningFilmRatings = ScreeningsPlan.FilmFanFilmRatings.Where(f => f.FilmId == FilmId);
            var builder = new StringBuilder();
            var filmFanList = ScreeningInfo.MyFriends;
            if (includeMe)
            {
                filmFanList.Insert(0, ScreeningInfo.Me);
            }
            foreach (string friend in filmFanList)
            {
                var friendRatings = screeningFilmRatings.Where(f => f.FilmFan == friend);
                bool friendHasRated = friendRatings.Any();
                if (AttendingFilmFans.Contains(friend))
                {
                    builder.Append(friend.Remove(1).ToUpper());
                    if(friendHasRated)
                    {
                        builder.Append(friendRatings.First().Rating.ToString());
                    }
                }
                else if(friendHasRated)
                {
                    builder.Append(friend.Remove(1).ToLower());
                    builder.Append(friendRatings.First().Rating.ToString());
                }
            }
            return builder.ToString();
        }

        public string ScreeningTitleIfDifferent(int? filmId=null)
        {
            string title = string.Empty;
            if (filmId != null)
            {
                if (filmId != FilmId)
                {
                    title = FilmTitle;
                }
            }
            if (title == string.Empty)
            {
                if (ScreeningTitle != FilmTitle)
                {
                    title = ScreeningTitle;
                }
            }
            return title == string.Empty ? title : $" - {title}";
        }
        #endregion

        #region Private Methods
        private string FromTillString()
        {
            return string.Format($"{StartTime.ToString(_timeFormat)}-{EndTime.ToString(_timeFormat)}");
        }

        private string GetCoincideKey()
        {
            string weekDay = $"{StartTime.DayOfWeek.ToString().Remove(3)}";
            string dateTime = $"{StartTime:yyyy-MM-dd HH:mm}";
            TimeSpan duration = EndTime - StartTime;
            return $"{Screen}, {weekDay} {dateTime} ({duration:hh\\:mm})";
        }
        #endregion
    }

    internal class ScreeningEqualityComparer : IEqualityComparer<Screening>
    {
        bool IEqualityComparer<Screening>.Equals(Screening screening, Screening otherScreening)
        {
            return screening.OriginalFilmId == otherScreening.OriginalFilmId
                && screening.Screen.ToString() == otherScreening.Screen.ToString()
                && screening.StartTime == otherScreening.StartTime
                && screening.EndTime == otherScreening.EndTime;
        }

        int IEqualityComparer<Screening>.GetHashCode(Screening screening)
        {
            string key = $"{screening.Screen}.{screening.StartTime}.{screening.EndTime}.{screening.OriginalFilmId}";
            return key.GetHashCode();
        }
    }
}
