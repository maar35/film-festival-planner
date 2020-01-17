﻿using System;
using System.Text;
using System.Collections.Generic;
using System.Linq;
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
        public const string _durationFormat = "hh\\:mm";
        private const string _dayOfWeekFormat = "dddd d MMMM";
        #endregion

        #region Private Members
        private readonly ScreeningInfo _screeningInfo;
        #endregion

        #region Properties
        public int FilmId { get; set; }
        public Film Film { get => ViewController.GetFilmById(FilmId); set => FilmId = value.FilmId; }
        public string FilmTitle => Film.Title;
        public Screen Screen { get; }
        public DateTime StartDate => DateTime.Parse(string.Format("{0}", StartTime.ToShortDateString()));
        public DateTime StartTime { get; }
        public DateTime EndTime { get; }
        public TimeSpan Duration => EndTime - StartTime;
        public int FilmsInScreening { get; }
        public string Extra { get; }
        public string QAndA { get; }
        public FilmRating Rating => Film.Rating;
        public string ScreeningTitle { get => _screeningInfo.ScreeningTitle; set => _screeningInfo.ScreeningTitle = value; }
        public List<string> AttendingFilmFans { get => _screeningInfo.Attendees; set => _screeningInfo.Attendees = value; }
        public bool IAttend => _screeningInfo.IAttend;
        public List<string> AttendingFriends => _screeningInfo.AttendingFriends;
        public bool SoldOut { get => _screeningInfo.SoldOut; set => _screeningInfo.SoldOut = value; }
        public bool TicketsBought { get => _screeningInfo.TicketsBought; set => _screeningInfo.TicketsBought = value; }
        public bool HasTimeOverlap => ViewController.OverlappingAttendedScreenings(this).Any();
        public bool HasNoTravelTime => ViewController.OverlappingAttendedScreenings(this, true).Any();
        public int TimesIAttendFilm => ScreeningsPlan.Screenings.Count(s => s.FilmId == FilmId && s.IAttend);
        public bool IsPlannable => TimesIAttendFilm == 0 && !HasNoTravelTime && !SoldOut;
        public int FilmScreeningCount => ViewController.FilmScreenings(FilmId).Count;
        public bool AutomaticallyPlanned { get => _screeningInfo.AutomaticallyPlanned; set => _screeningInfo.AutomaticallyPlanned = value; }
        public ScreeningInfo.TicketsStatus TicketStatus => ScreeningInfo.GetTicketStatus(IAttend, TicketsBought);
        public ScreeningInfo.ScreeningStatus Status { get => _screeningInfo.Status; set => _screeningInfo.Status = value; }
        public ScreeningInfo.Warning Warning { get; set; } = ScreeningInfo.Warning.NoWarning;
        public List<IFilmOutlinable> FilmOutlinables { get; private set; } = new List<IFilmOutlinable> { };
        static public Action<Screening> GoToScreening { get; private set; }
        #endregion

        #region Static Properties
        public static TimeSpan TravelTime { get; set; }
        public static bool InOutliningOverlaps { get; set; } = false;
        #endregion

        #region Constructors
        public Screening() { }

        public Screening(string screeningText)
        {
            // Assign the fields of the input string.
            string[] fields = screeningText.Split(';');
            int filmId = int.Parse(fields[0]);
            DateTime date = DateTime.Parse(fields[1]);
            string screen = fields[2];
            string startTime = fields[3];
            string endTime = fields[4];
            int filmsInScreening = int.Parse(fields[5]);
            string extra = fields[6];
            string qAndA = fields[7];            //string screeningStatus = fields[0];

            // Assign properties that need calculation.
            DateTime startDate = DateTimeFromParsedData(date, startTime);
            DateTime endDate = DateTimeFromParsedData(date, endTime);
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
        public override string WriteHeader()
        {
            string headerFmt = "weekday;date;{0};screen;starttime;endtime;title;filmsinscreening;extra;qanda;url;mainfilmdescription";
            return string.Format(headerFmt, ScreeningInfo.FilmFansString().Replace(',', ';'));
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
            fields.Add(EndTime.ToString(_timeFormat));
            fields.Add(Film.ToString());
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
            var travelTime = useTravelTime ? TravelTime : TimeSpan.Zero;
            return otherScreening.StartTime <= EndTime + travelTime
                && otherScreening.EndTime >= StartTime - travelTime;
        }

        public void SetOverlappingScreenings()
        {
            if (FilmOutlinables.Count == 0)
            {
                Func<Screening, bool> filmHasSuperRating = s => AnalyserDialogController.FilterFilmByRating(s.Film);
                Func<Screening, bool> AttendedByFriend = s => s.Status == ScreeningInfo.ScreeningStatus.AttendedByFriend;
                var screenings = ViewController.OverlappingScreenings(this, true)
                                               .Where(s => filmHasSuperRating(s) || AttendedByFriend(s))
                                               .OrderByDescending(s => s.Film.MaxRating);
                var level = FilmOutlineLevel.Level.OverlappingScreening;
                var controller = ((AppDelegate)NSApplication.SharedApplication.Delegate).AnalyserDialogController;
                GoToScreening = controller.GoToScreening;
                foreach (var screening in screenings)
                {
                    var filmOutlineLevel = new FilmOutlineLevel(screening, level, controller.GoToScreening);
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
            return string.Format("{0} {1}{2}", ToMenuItemString(), ShortAttendingFriendsString(), ScreeningTitleIfDifferent());
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
            StringBuilder builder = new StringBuilder();
            foreach (string friend in ScreeningInfo.MyFriends)
            {
                var friendRatings = screeningFilmRatings.Where(f => f.FilmFan == friend);
                bool friendHasRated = friendRatings.Any();
                if (AttendingFriends.Contains(friend))
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
        #endregion

        #region Private Methods
        private DateTime DateTimeFromParsedData(DateTime date, string time)
        {
            string parseString = string.Format("{0} {1}", date.ToShortDateString(), time);
            return DateTime.Parse(parseString);
        }

        private string FromTillString()
        {
            return string.Format("{0}-{1}", StartTime.ToString(_timeFormat), EndTime.ToString(_timeFormat));
        }

        private static string EntityToUnicode(string html)
        {
            var replacements = new Dictionary<string, string>();
            var regex = new Regex("&([a-z]{2,7});");
            foreach (Match match in regex.Matches(html))
            {
                if (!replacements.ContainsKey(match.Value))
                {
                    //var unicode = System.Net.WebUtility.HtmlDecode(match.Value);
                    //if (unicode.Length == 1)
                    //{
                    //    replacements.Add(match.Value, string.Concat("&#", Convert.ToInt32(unicode[0]), ";"));
                    //}
                    replacements.Add(match.Value, regex.Replace(match.Value, @"[$1]"));
                }
            }
            foreach (var replacement in replacements)
            {
                html = html.Replace(replacement.Key, replacement.Value);
            }
            return html;
        }
        #endregion
    }
}
