using System;
using System.Text;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

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
        private const string _dateFormat = "yyyy-MM-dd";
        private const string _timeFormat = "HH:mm";
        private const string _durationFormat = "hh\\:mm";
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
        public bool IAttend { get => _screeningInfo.IAttend; }
        public List<string> AttendingFriends => _screeningInfo.AttendingFriends;
        public bool SoldOut { get => _screeningInfo.SoldOut; set => _screeningInfo.SoldOut = value; }
        public bool TicketsBought { get => _screeningInfo.TicketsBought; set => _screeningInfo.TicketsBought = value; }
        public ScreeningInfo.TicketsStatus TicketStatus => ScreeningInfo.GetTicketStatus(IAttend, TicketsBought);
        public ScreeningInfo.ScreeningStatus Status { get => _screeningInfo.Status; set => _screeningInfo.Status = value; }
        public ScreeningInfo.Warning Warning { get; set; } = ScreeningInfo.Warning.NoWarning;
        #endregion

        #region Static Properties
        public static TimeSpan TravelTime { get; set; }
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
            return string.Format("{0}\n{1} {2} {3} {4} {5}", ScreeningTitle, DayString(StartTime), DurationString(), Screen, Duration.ToString(_durationFormat), Rating);
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
        #endregion

        #region Private Methods
        private DateTime DateTimeFromParsedData(DateTime date, string time)
        {
            string parseString = string.Format("{0} {1}", date.ToShortDateString(), time);
            return DateTime.Parse(parseString);
        }

        private string DurationString()
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

        #region Public Methods
        public static string HtmlDecode(string html)
        {
            var htmlRe = new Regex(@"&amp;([a-z]{2,7});", RegexOptions.CultureInvariant);
            return htmlRe.Replace(html, @":$1:").Replace("&#039;", "'").Replace(";", ".,").Replace(":nbsp:", " ").Replace(":euml:", @"ë").Replace("ldquo", @"'").Replace("lsquo", @"'").Replace("rdquo", @"'").Replace("rsquo", @"'");
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

        public bool HasPlannableStatus()
        {
            return Status == ScreeningInfo.ScreeningStatus.Free && !SoldOut;
        }

        public bool Overlaps(Screening otherScreening, bool useTravelTime = false)
        {            
            var travelTime = useTravelTime ? TravelTime : TimeSpan.Zero;
            return otherScreening.StartTime <= EndTime + travelTime
                && otherScreening.EndTime >= StartTime - travelTime;

        }
        #endregion

        #region Display Methods
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
            return string.Format("{0} {1} ({2})", StartDate.ToString(_dayOfWeekFormat), DurationString(), Duration.ToString(_durationFormat));
        }

        public string ToMenuItemString()
        {
            return string.Format("{0} {1} {2}", DayString(StartTime), Screen, StartTime.ToString(_timeFormat));
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

        public string AttendeesString()
        {
            return string.Join(", ", AttendingFilmFans);
        }

        public string ScreeningStringForLabel(bool withDay = false)
        {
            string dayString = withDay ? string.Format("{0} ", DayString(StartTime)) : string.Empty;
            return string.Format("{0}{1} {2} {3} {4}", dayString, Screen, DurationString(), Rating, ShortFriendsString());
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
    }
}
