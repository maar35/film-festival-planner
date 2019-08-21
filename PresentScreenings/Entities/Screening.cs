﻿using System;
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

    public class Screening : IComparable, ICanWriteList
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
        public bool IAttend { get => _screeningInfo.IAttend; set => _screeningInfo.IAttend = value; }
        public List<string> AttendingFriends => _screeningInfo.AttendingFriends;
        public bool SoldOut { get => _screeningInfo.SoldOut; set => _screeningInfo.SoldOut = value; }
        public bool TicketsBought { get => _screeningInfo.TicketsBought; set => _screeningInfo.TicketsBought = value; }
        public ScreeningInfo.TicketsStatus TicketStatus => ScreeningInfo.GetTicketStatus(IAttend, TicketsBought);
        public ScreeningInfo.ScreeningStatus Status { get => _screeningInfo.Status; set => _screeningInfo.Status = value; }
        public ScreeningInfo.Warning Warning { get; set; } = ScreeningInfo.Warning.NoWarning;
        #endregion

        #region Constructors
        public Screening(string screeningText, List<Screen> screens, List<Film> films)
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
            Film = (from Film film in films where film.FilmId == filmId select film).First();
            Screen = (from Screen s in screens where s.ToString() == screen select s).First();
            StartTime = startDate;
            EndTime = endDate;
            FilmsInScreening = filmsInScreening;
            Extra = extra;
            QAndA = qAndA;
            _screeningInfo =
                (
                    from ScreeningInfo s in ScreeningsPlan.ScreeningInfos
                    where s.FilmId == FilmId && s.Screen == Screen && s.StartTime == StartTime
                    select s
                ).First();
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return string.Format("{0}\n{1} {2} {3} {4} {5}", ScreeningTitle, DayString(StartTime), DurationString(), Screen, Duration.ToString(_durationFormat), Rating);
        }
        #endregion

        #region Interface Implementations
        public int CompareTo(object obj)
        {
            return StartTime.CompareTo(((Screening)obj).StartTime);
        }

        string ICanWriteList.Serialize()
        {
            string line = string.Join(
                ';',
                FilmId,
                StartTime.ToString(_dateFormat),
                Screen,
                StartTime.ToString(_timeFormat),
                EndTime.ToString(_timeFormat),
                FilmsInScreening,
                Extra,
                QAndA
            );
            return line;
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
            string headerFmt = "filmid;date;screen;starttime;endtime;filmsinscreening;extra;qanda";
            return string.Format(headerFmt, ScreeningInfo.Friends());
        }

        public static string WriteOverviewHeader()
        {
            string headerFmt = "weekday;date;maarten;{0};screen;starttime;endtime;title;filmsinscreening;extra;qanda;url;mainfilmdescription";
            return string.Format(headerFmt, ScreeningInfo.Friends().Replace(',', ';'));
        }

        public static string WriteOverviewRecord(Screening screening)
        {
            string line = string.Empty;
            List<string> fields = new List<string> { };
            fields.Add(screening.StartTime.DayOfWeek.ToString().Remove(3));
            fields.Add(screening.StartTime.ToString(_dateFormat));
            fields.Add(ScreeningInfo.BoolToString[screening.IAttend]);
            foreach (var friend in ScreeningInfo.MyFriends)
            {
                fields.Add(ScreeningInfo.BoolToString[screening.FriendAttends(friend)]);
            }
            fields.Add(screening.Screen.ToString());
            fields.Add(screening.StartTime.ToString(_timeFormat));
            fields.Add(screening.EndTime.ToString(_timeFormat));
            fields.Add(screening.Film.ToString());
            fields.Add(screening.FilmsInScreening.ToString());
            fields.Add(screening.Extra);
            fields.Add(screening.QAndA);
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

        public bool FriendAttends(string friend)
        {
            return AttendingFriends.Contains(friend);
        }

        public void ToggleMyAttendance()
        {
            IAttend = !IAttend;
        }

        public void ToggleFriendAttendance(string friend)
        {
            if (AttendingFriends.Contains(friend))
            {
                AttendingFriends.Remove(friend);
            }
            else
            {
                AttendingFriends.Add(friend);
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

        public string AttendeesString(bool inlcludeMe = true)
        {
            var attendingFilmFans = new List<string>(AttendingFriends);
            if (inlcludeMe && IAttend)
            {
                attendingFilmFans.Insert(0, ScreeningInfo.Me);
            }
            return string.Join(", ", attendingFilmFans);
        }

        public string ScreeningStringForLabel(bool withDay = false)
        {
            string dayString = withDay ? string.Format("{0} ", DayString(StartTime)) : string.Empty;
            return string.Format("{0}{1} {2} {3} {4}", dayString, Screen, DurationString(), Rating, ShortFriendsString());
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
            var screeningFilmRatings = ScreeningsPlan.FilmFanFilmRatings.Where(f => f.FilmId == FilmId);
            StringBuilder builder = new StringBuilder();
            foreach (string friend in ScreeningInfo.MyFriends)
            {
                var friendRatings = screeningFilmRatings.Where(f => f.FilmFan == friend);
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
            return string.Format($" - {ScreeningTitle}");
        }
        #endregion
    }
}