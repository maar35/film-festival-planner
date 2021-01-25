using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Represents the data that defines a screening, enriched with related
    /// information like attendance, availability of tickets and whether another
    /// screening is attended at the same time or the film is already planned.
    /// </summary>

    public class Screening : ListStreamer, IComparable, IFilmOutlinable
    {
        #region Constant Private Members
        private const string _dateFormat = "yyyy-MM-dd";
        private const string _timeFormat = "HH:mm";
        private const string _onlineTimeFormat = "HH:mm ddd d-M";
        private const string _dtFormat = "ddd dd:MM HH:mm";
        private const string _dayOfWeekFormat = "dddd d MMMM";
        private const string _durationFormat = "hh\\:mm";
        #endregion

        #region Private Members
        private readonly ScreeningInfo _screeningInfo;
        #endregion

        #region Properties
        public int FilmId { get; set; }
        public Screen Screen { get; }
        public DateTime StartTime { get; }
        public DateTime EndTime { get; }
        public int FilmsInScreening { get; }
        public int? CombinationProgramId { get; }
        public string Extra { get; }
        public string QAndA { get; }
        #endregion

        #region Calculated Properties
        public Film Film { get => ViewController.GetFilmById(FilmId); set => FilmId = value.FilmId; }
        public string FilmTitle => Film.Title;
        public DateTime StartDate => DateTime.Parse(string.Format("{0}", StartTime.ToShortDateString()));
        public TimeSpan Duration => EndTime - StartTime;
        public FilmRating Rating => Film.Rating;
        public string ScreeningTitle { get => _screeningInfo.ScreeningTitle; set => _screeningInfo.ScreeningTitle = value; }
        public List<string> AttendingFilmFans { get => _screeningInfo.Attendees; set => _screeningInfo.Attendees = value; }
        public bool IAttend => _screeningInfo.IAttend;
        public List<string> AttendingFriends => _screeningInfo.AttendingFriends;
        public bool SoldOut { get => _screeningInfo.SoldOut; set => _screeningInfo.SoldOut = value; }
        public bool TicketsBought { get => _screeningInfo.TicketsBought; set => _screeningInfo.TicketsBought = value; }
        public bool HasTimeOverlap => ViewController.OverlappingAttendedScreenings(this).Any();
        public bool HasNoTravelTime => ViewController.OverlappingAttendedScreenings(this, true).Any();
        private Screen.ScreenType ScreenType => Screen.Type;
        public bool OnLine => ScreenType == Screen.ScreenType.OnLine;
        public bool Location => ScreenType == Screen.ScreenType.Location;
        public int TimesIAttendFilm => ScreeningsPlan.Screenings.Count(s => s.FilmId == FilmId && s.IAttend);
        public bool IsPlannable => TimesIAttendFilm == 0 && !HasNoTravelTime && !SoldOut;
        public int FilmScreeningCount => ViewController.FilmScreenings(FilmId).Count;
        public bool AutomaticallyPlanned { get => _screeningInfo.AutomaticallyPlanned; set => _screeningInfo.AutomaticallyPlanned = value; }
        public ScreeningInfo.TicketsStatus TicketStatus => ScreeningInfo.GetTicketStatus(IAttend, TicketsBought);
        public ScreeningInfo.ScreeningStatus Status { get => _screeningInfo.Status; set => _screeningInfo.Status = value; }
        public ScreeningInfo.Warning Warning { get; set; } = ScreeningInfo.Warning.NoWarning;
        public List<IFilmOutlinable> FilmOutlinables { get; private set; } = new List<IFilmOutlinable> { };
        #endregion

        #region Static Properties
        public static Action<Screening> GoToScreening { get; set; }
        public static TimeSpan TravelTime { get; set; }
        public static bool InOutliningOverlaps { get; set; } = false;
        #endregion

        #region Constructors
        public Screening() { }

        public Screening(Screening screening, DateTime day)
        {
            FilmId = screening.Film.FilmId;
            Film = screening.Film;
            Screen = screening.Screen;
            StartTime = DateTimeFromParsedData(day.Date, "09:00");
            EndTime = DateTimeFromParsedData(day.Date, "23:59");
            FilmsInScreening = 1;
            Extra = screening.Extra;
            QAndA = screening.QAndA;
            _screeningInfo = screening._screeningInfo;
        }

        public Screening(string screeningText)
        {
            // Assign the fields of the input string.
            string[] fields = screeningText.Split(';');
            int filmId = int.Parse(fields[0]);
            string screen = fields[1];
            string startTime = fields[2];
            string endTime = fields[3];
            int filmsInScreening = int.Parse(fields[4]);
            string combinationIdStr = fields[5];
            string extra = fields[6];
            string qAndA = fields[7];

            // Assign properties that need calculation.
            DateTime startDate = DateTime.Parse(startTime);
            DateTime endDate = DateTime.Parse(endTime);
            if (endDate < startDate)
            {
                endDate = endDate.AddDays(1);
            }
            FilmId = filmId;
            Film = (from Film film in ScreeningsPlan.Films where film.FilmId == filmId select film).First();
            Screen = (from Screen s in ScreeningsPlan.Screens where s.ToString() == screen select s).First();
            StartTime = startDate;
            EndTime = endDate;
            FilmsInScreening = filmsInScreening;
            CombinationProgramId = int.TryParse(combinationIdStr, out int outcome) ? (int?)outcome : null;
            Extra = extra;
            QAndA = qAndA;
            var screeningInfos = ScreeningsPlan.ScreeningInfos.Where(s => s.FilmId == FilmId && s.Screen == Screen && s.StartTime == StartTime).ToList();
            if (screeningInfos.Count == 0)
            {
                _screeningInfo = new ScreeningInfo(FilmId, Screen, StartTime);
                ScreeningsPlan.ScreeningInfos.Add(_screeningInfo);
            }
            else
            {
                _screeningInfo = screeningInfos.First();
            }
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return string.Format("{0}\n{1} {2} {3} {4} {5}", ScreeningTitle, DayString(StartTime), FromTillString(), Screen, DurationString(), Rating);
        }

        public override bool ListFileIsMandatory()
        {
            // Even if FilmRatingDialogController.OnlyFilmsWithScreenings is set
            // to false, we do need at least one screening to fill the day plan.
            return true;
        }

        public override string WriteHeader()
        {
            string headerFmt = "weekday;date;{0};screen;starttime;endtime;title;filmsinscreening;extra;qanda;url;mainfilmdescription";
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
            string line = string.Empty;
            List<string> fields = new List<string> { };

            fields.Add(StartTime.DayOfWeek.ToString().Remove(3));
            fields.Add(StartTime.ToString(_dateFormat));
            foreach (var filmFan in ScreeningInfo.FilmFans)
            {
                fields.Add(ScreeningInfo.BoolToString[FilmFanAttends(filmFan)]);
            }
            fields.Add(Screen.ToString());
            fields.Add(StartTime.ToString(_timeFormat));
            fields.Add(EndTime.ToString(Location ? _timeFormat : _onlineTimeFormat));
            fields.Add($"{Film} ({Film.MinutesString})");
            fields.Add(FilmsInScreening.ToString());
            fields.Add(Extra);
            fields.Add(QAndA);
            var filmInfoList = ScreeningsPlan.FilmInfos.Where(i => i.FilmId == FilmId);
            var filmInfo = filmInfoList.Count() == 1 ? filmInfoList.First() : null;
            fields.Add(filmInfo != null ? filmInfo.Url : "");
            fields.Add(filmInfo != null ? HtmlDecode(filmInfo.FilmDescription) : "");

            return string.Join(";", fields);
        }
        #endregion

        #region Interface Implementations
        public int CompareTo(object obj)
        {
            return StartTime.CompareTo(((Screening)obj).StartTime);
        }

        bool IFilmOutlinable.ContainsFilmOutlinables()
        {
            return FilmOutlinables.Count > 0;
        }

        void IFilmOutlinable.SetTitle(NSTextField view)
        {
            view.StringValue = ToMenuItemString();
            view.LineBreakMode = NSLineBreakMode.TruncatingMiddle;
        }

        public void SetGo(NSView view)
        {
            ScreeningsView.DisposeSubViews(view);
            var rect = new CGRect(0, 0, view.Frame.Width, view.Frame.Height);
            var infoButton = new FilmScreeningControl(rect, this);
            infoButton.ReDraw();
            infoButton.ScreeningInfoAsked += (sender, e) => GoToScreening(this);
            infoButton.Selected = false;
            view.AddSubview(infoButton);
        }

        void IFilmOutlinable.SetRating(NSTextField view)
        {
            view.StringValue = string.Empty;
        }

        void IFilmOutlinable.SetInfo(NSTextField view)
        {
            ColorView.SetScreeningColor(this, view);
            view.StringValue = ScreeningStringForLabel(true);
            view.LineBreakMode = NSLineBreakMode.TruncatingTail;
        }
        #endregion

        #region Public Methods
        public static string HtmlDecode(string html)
        {
            var htmlRe = new Regex(@"&amp;([a-zA-Z]{2,7});", RegexOptions.CultureInvariant);
            return htmlRe.Replace(html, @":$1:").Replace("&#039;", "'")
                .Replace(";", ".,")
                .Replace(":nbsp:", " ")
                .Replace(":aacute:", @"á").Replace(":auml:", @"ä")
                .Replace(":euml:", @"ë").Replace(":eacute:", @"é").Replace(":egrave:", @"è").Replace(":Eacute:", @"É")
                .Replace(":iacute:", @"í").Replace(":iuml:", @"ï")
                .Replace(":oacute:", @"ó")
                .Replace(":Scaron:", @"Š")
                .Replace(":ndash:", @"–")
                .Replace(":ldquo:", @"“").Replace(":lsquo:", @"‘").Replace(":rdquo:", @"”").Replace(":rsquo:", @"’").Replace(":quot:", "'");
        }

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
            if (OnLine || otherScreening.OnLine)
            {
                return false;
            }
            var travelTime = useTravelTime ? TravelTime : TimeSpan.Zero;
            return otherScreening.StartTime <= EndTime + travelTime
                && otherScreening.EndTime >= StartTime - travelTime;
        }

        public void SetOverlappingScreenings()
        {
            if (FilmOutlinables.Count == 0)
            {
                Func<Screening, bool> Attending = s => s.Status == ScreeningInfo.ScreeningStatus.Attending;
                var screenings = ViewController.OverlappingScreenings(this, true)
                                               .Where(s => Attending(s))
                                               .OrderByDescending(s => s.Film.MaxRating);
                var level = FilmOutlineLevel.Level.OverlappingScreening;
                foreach (var screening in screenings)
                {
                    var filmOutlineLevel = new FilmOutlineLevel(screening, level, GoToScreening);
                    FilmOutlinables.Add(filmOutlineLevel);
                }
            }
        }
        #endregion

        #region Public Display Methods
        public static string DayString(DateTime date)
        {
            return string.Format("{0}{1}", date.DayOfWeek.ToString().Remove(3), date.Day.ToString());
        }

        public static string LongDayString(DateTime date)
        {
            return string.Format("{0} {1}", date.DayOfWeek.ToString().Remove(3), date.ToString(_dateFormat));
        }

        public string ToLongTimeString()
        {
            return string.Format("{0} {1} ({2}){3}", StartDate.ToString(_dayOfWeekFormat), FromTillString(), DurationString(), AppendingExtraTimesString());
        }

        public string ToMenuItemString()
        {
            return $"{DayString(StartTime)} {Screen} {StartTime.ToString(_timeFormat)} {ExtraTimeSymbolsString()}";
        }

        public string ToFilmScreeningLabelString()
        {
            if (Location)
            {
                return string.Format("{0} {1}{2}", ToMenuItemString(), ShortAttendingFriendsString(), ScreeningTitleIfDifferent());
            }
            return $"{DayString(StartTime)} {Screen} {StartTime.ToString(_dtFormat)}-{EndTime.ToString(_dtFormat)} {ExtraTimeSymbolsString()} {ShortAttendingFriendsString()}{ScreeningTitleIfDifferent()}";
        }

        public string ToScreeningLabelString(bool withDay = false)
        {
            return string.Format("{0}\n{1}", ScreeningTitle, ScreeningStringForLabel(withDay));
        }

        public string ToPlannedScreeningString()
        {
            return string.Format("{0} {1}", ToLongTimeString(), ScreeningTitle);
        }

        public string ToConsideredScreeningString()
        {
            string iAttend(bool b) => b ? "M" : string.Empty;
            return string.Format("{0} {1} {2} {3} {4} {5} {6}", Film, FilmScreeningCount, Screen,
                                 LongDayString(StartTime), DurationString(), iAttend(IAttend),
                                 ShortFriendsString());
        }

        public string DurationString()
        {
            return Duration.ToString(_durationFormat);
        }

        public string AppendingExtraTimesString()
        {
            string extrasString = ExtraTimeSymbolsString();
            return extrasString == string.Empty ? extrasString : $" ({Film.Duration.ToString(_durationFormat)} + {extrasString})";
        }

        public string ExtraTimeSymbolsString()
        {
            string extrasString = (Extra == string.Empty ? Extra : "V") + (QAndA == string.Empty ? QAndA : "Q");
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
        /// </summary>
        /// <returns></returns>
        public string ShortFriendsString()
        {
            var screeningFilmRatings = ScreeningsPlan.FilmFanFilmRatings.Where(f => f.FilmId == FilmId);
            var builder = new StringBuilder();
            var friends = ScreeningInfo.MyFriends;
            foreach (string friend in friends)
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

        public string ScreeningTitleIfDifferent()
        {
            if (ScreeningTitle == FilmTitle)
            {
                return string.Empty;
            }
            return string.Format($" - {ScreeningTitle}");
        }

        public static DateTime DateTimeFromParsedData(DateTime date, string time)
        {
            string parseString = string.Format("{0} {1}", date.ToShortDateString(), time);
            return DateTime.Parse(parseString);
        }
        #endregion

        #region Private Methods
        private string FromTillString()
        {
            return string.Format("{0}-{1}", StartTime.ToString(_timeFormat), EndTime.ToString(_timeFormat));
        }
                    #endregion
    }
}
