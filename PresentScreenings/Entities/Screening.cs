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

    public class Screening : IComparable
    {
        #region Constant Private Members
        const string _dateFormat = "yyyy-MM-dd";
        const string _timeFormat = "HH:mm";
        const string _durationFormat = "hh\\:mm";
        const string _dayOfWeekFormat = "dddd d MMMM";
        #endregion

        #region Private Members
        int _filmId;
        Film _film;
        readonly string _screeningTitle;
        readonly Screen _screen;
        readonly DateTime _startTime;
        readonly DateTime _endTime;
        readonly int _filmsInScreening;
        readonly string _extra;
        readonly string _qAndA;
        bool _iAttend;
        List<string> _attendingFriends;
        bool _ticketsBought;
        bool _soldOut;
        ScreeningStatus.Status _status;
        ScreeningStatus.Warning _warning = ScreeningStatus.Warning.NoWarning;
        readonly List<FilmFanFilmRating> _friendFilmRatings;
        #endregion

        #region Properties
        public int FilmId => _filmId;
        //public int FilmId { get => _filmId; set => _filmId = value; } //can't be used as long as _film is a property.
        public string FilmTitle => _film.Title;
        public string ScreeningTitle => _screeningTitle;
        public Screen Screen => _screen;
        public DateTime StartDate => DateTime.Parse(string.Format("{0}", StartTime.ToShortDateString()));
        public DateTime StartTime => _startTime;
        public DateTime EndTime => _endTime;
        public TimeSpan Duration => EndTime - StartTime;
        public int FilmsInScreening => _filmsInScreening;
        public string Extra => _extra;
        public string QAndA => _qAndA;
        public FilmRating Rating { get => _film.Rating; }
        public List<string> AttendingFriends => _attendingFriends;
        public bool IAttend => _iAttend;
        public bool SoldOut { get => _soldOut; set => _soldOut = value; }
        public bool TicketsBought { get => _ticketsBought; set => _ticketsBought = value; }
        public ScreeningStatus.TicketsStatus TicketStatus => ScreeningStatus.GetTicketStatus(_iAttend, _ticketsBought);
        public ScreeningStatus.Status Status { get => _status; set => _status = value; }
        public ScreeningStatus.Warning Warning { get => _warning; set => _warning = value; }
        #endregion

        #region Constructors
        public Screening(string screeningText, List<Screen> screens, List<Film> films, List<FilmFanFilmRating> ratings)
        {
            string[] fields = screeningText.Split(';');

            string screeningStatus = fields[0];
            string myAttendance = fields[1];
            var myFriendsAttendances = new List<string>(fields[2].Split(','));
            string weekdayMonthday = fields[3]; // report-only:
            string screen = fields[4];
            string startTime = fields[5];
            string endTime = fields[6];
            string title = fields[7];
            int filmsInScreening = int.Parse(fields[8]);
            string extra = fields[9];
            string qAndA = fields[10];
            string ticketsBought = fields[11];
            string soldOut = fields[12];
            DateTime date = DateTime.Parse(fields[13]);
            int filmId = int.Parse(fields[14]);

            DateTime startDate = DateTimeFromParsedData(date, startTime);
            DateTime endDate = DateTimeFromParsedData(date, endTime);
            if (endDate < startDate)
            {
                endDate = endDate.AddDays(1);
            }
            _screeningTitle = title;
            _filmId = filmId;
            _friendFilmRatings = ratings;
            _film = (from Film film in films where film.FilmId == filmId select film).ElementAt(0);
            _screen = (from Screen s in screens where s.ToString() == screen select s).ElementAt(0);
            _startTime = startDate;
            _endTime = endDate;
            _filmsInScreening = filmsInScreening;
            _extra = extra;
            _qAndA = qAndA;
            _status = ScreeningStatus.GetScreeningStatus(screeningStatus, myFriendsAttendances);
            _ticketsBought = ScreeningStatus.StringToBool[ticketsBought];
            _soldOut = ScreeningStatus.StringToBool[soldOut];
            _iAttend = ScreeningStatus.StringToBool[myAttendance];
            _attendingFriends = ScreeningStatus.AttendingFriends(myFriendsAttendances);
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return string.Format("{0}\n{1} {2} {3} {4} {5}", ScreeningTitle, DayString(StartTime), DurationString(), _screen, Duration.ToString(_durationFormat), Rating);
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

        private static string TimeString(DateTime time)
        {
            return time.ToString(_timeFormat);
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
        public static string WriteHeader()
        {
            string headerFmt = "blocked;maarten;{0};startdm;theatre;starttime;endtime;title;filmsinshow;extra;qanda;ticketsbought;soldout;date;filmid";
            return string.Format(headerFmt, ScreeningStatus.Friends());
        }

        public static string Serialize(Screening screening)
        {
            string line = string.Join(
                ";",
                ScreeningStatus.GetScreeningStatusString(screening._status),
                ScreeningStatus.BoolToString[screening._iAttend],
                ScreeningStatus.AttendingFriendsString(screening._attendingFriends),
                DayString(screening._startTime),
                screening._screen,
                screening._startTime.ToString(_timeFormat),
                screening._endTime.ToString(_timeFormat),
                screening._screeningTitle,
                screening._filmsInScreening,
                screening._extra,
                screening._qAndA,
                ScreeningStatus.BoolToString[screening._ticketsBought],
                ScreeningStatus.BoolToString[screening._soldOut],
                screening._startTime.ToString(_dateFormat),
                screening._filmId
            );
            return line;
        }

        public static string WriteOverviewHeader()
        {
            string headerFmt = "weekday;date;maarten;{0};screen;starttime;endtime;title;filmsinshow;extra;qanda;url;mainfilmdescription";
            return string.Format(headerFmt, ScreeningStatus.Friends().Replace(',', ';'));
        }

        public static string WriteOverviewRecord(Screening screening)
        {
            string line = string.Empty;
            List<string> fields = new List<string> { };
            fields.Add(screening._startTime.DayOfWeek.ToString().Remove(3));
            fields.Add(screening._startTime.ToString(_dateFormat));
            fields.Add(ScreeningStatus.BoolToString[screening._iAttend]);
            foreach (var friend in ScreeningStatus.MyFriends)
            {
                fields.Add(ScreeningStatus.BoolToString[screening.FriendAttends(friend)]);
            }
            fields.Add(screening._screen.ToString());
            fields.Add(screening._startTime.ToString(_timeFormat));
            fields.Add(screening._endTime.ToString(_timeFormat));
            fields.Add(screening._film.ToString());
            fields.Add(screening._filmsInScreening.ToString());
            fields.Add(screening._extra);
            fields.Add(screening._qAndA);
            var filmInfoList = ScreeningsPlan.FilmInfos.Where(i => i.FilmId == screening.FilmId);
            var filmInfo = filmInfoList.Count() == 1 ? filmInfoList.First() : null;
            fields.Add(filmInfo != null ? filmInfo.Url : "");
            fields.Add(filmInfo != null ? HtmlDecode(filmInfo.FilmDescription) : "");
            return string.Join(";", fields.ToArray());
        }

        public static string HtmlDecode(string html)
        {
            var htmlRe = new Regex(@"&amp;([a-z]{2,7});", RegexOptions.CultureInvariant);
            return htmlRe.Replace(html, @":$1:").Replace("&#039;", "'").Replace(";", ".,").Replace(":nbsp:", " ").Replace(":euml:", @"ë").Replace("ldquo", @"'").Replace("lsquo", @"'").Replace("rdquo", @"'").Replace("rsquo", @"'");
        }

        public void SetFilm(int filmId, Film film)
        {
            _filmId = filmId;
            _film = film;
        }

        public bool FriendAttends(string friend)
        {
            return _attendingFriends.Contains(friend);
        }

        public void ToggleMyAttendance()
        {
            _iAttend = !_iAttend;
        }

        public void ToggleFriendAttendance(string friend)
        {
            if (_attendingFriends.Contains(friend))
            {
                _attendingFriends.Remove(friend);
            }
            else
            {
                _attendingFriends.Add(friend);
            }
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
            return string.Format("{0} {1} {2}", DayString(StartTime), _screen, StartTime.ToString(_timeFormat));
        }

        public string ToFilmScreeningLabelString()
        {
            return string.Format("{0} {1}{2}", ToMenuItemString(), ShortAttendingFriendsString(), ScreeningTitleIfDifferent());
        }

        public string ToScreeningLabelString(bool withDay = false)
        {
            return string.Format("{0}\n{1}", ScreeningTitle, ScreeningStringForLabel(withDay));
        }

        public string AttendeesString(bool inlcludeMe = true)
        {
            var attendingFilmFans = new List<string>(_attendingFriends);
            if (inlcludeMe && _iAttend)
            {
                attendingFilmFans.Insert(0, ScreeningStatus.Me);
            }
            return string.Join(", ", attendingFilmFans);
        }

        public string ScreeningStringForLabel(bool withDay = false)
        {
            string dayString = withDay ? string.Format("{0} ", DayString(StartTime)) : string.Empty;
            return string.Format("{0}{1} {2} {3} {4}", dayString, _screen, DurationString(), Rating, ShortFriendsString());
        }

        public string ShortAttendingFriendsString()
        {
            StringBuilder abbreviationBuilder = new StringBuilder();
            foreach (var friend in AttendingFriends)
            {
                abbreviationBuilder.Append(friend.Remove(1));
            }
            return abbreviationBuilder.ToString();
        }

        public string ShortFriendsString()
        {
            var screeningFriendFilmRatings = _friendFilmRatings.Where(f => f.FilmId == _filmId);
            StringBuilder builder = new StringBuilder();
            foreach (string friend in ScreeningStatus.MyFriends)
            {
                var friendRatings = screeningFriendFilmRatings.Where(f => f.FilmFan == friend);
                bool friendHasRated = friendRatings.Any();
                bool friendAttends = AttendingFriends.Contains(friend);
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
            return string.Format(" - {0}", ScreeningTitle);
        }
        #endregion

        #region Interface Implementation
        public int CompareTo(object obj)
        {
            return _startTime.CompareTo(((Screening)obj).StartTime);
        }
        #endregion
    }
}