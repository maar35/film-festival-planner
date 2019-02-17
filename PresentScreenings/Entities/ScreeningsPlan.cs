using System.Collections.Generic;
using System;
using System.Linq;
using System.IO;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Represents all screenings of the film festival and is responsible for
    /// adequate access to this information.
    /// </summary>

    public class ScreeningsPlan
    {
        #region Constants
        public const string FestivalYear = "2019";
        #endregion

        #region Private members
        static string _homeFolder = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
        static string _directory = HomeFolder + @"/Documents/Film/IFFR/IFFR" + FestivalYear + @"/Screenings Plan";
        static string _screensFile = Path.Combine(_directory, "screens.csv");
        static string _filmsFile = Path.Combine(_directory, "films.csv");
        static string _screeningsFile = Path.Combine(_directory, "screenings.csv");
        static string _friendFilmRatingsFile = Path.Combine(_directory, "friendfilmratings.csv");
        static string _filmInfoFile = Path.Combine(_directory, "filminfo.xml");
        List<Film> _films;
        List<Screen> _screens;
        List<DateTime> _days;
        Dictionary<DateTime, List<Screen>> _dayScreens;
        Dictionary<DateTime, Dictionary<Screen, List<Screening>>> _screenScreenings;
        static private List<FilmInfo> _filmInfos;
        int _currDayNumber;
        int _currScreenNumber;
        int _currScreenScreeningNumber;
        #endregion

        #region Properties
        public static string HomeFolder => _homeFolder;
        public Dictionary<DateTime, Dictionary<Screen, List<Screening>>> ScreenScreenings => _screenScreenings;
        public Screen CurrScreen => _dayScreens[CurrDay][_currScreenNumber];
        public Screening CurrScreening => _screenScreenings[CurrDay][CurrScreen][_currScreenScreeningNumber];
        public List<DateTime> FestivalDays => _days;
        public List<Screen> CurrDayScreens => _dayScreens[CurrDay];
        public List<Screen> Screens => _screens;
        public List<Film> Films => _films;
        public DateTime CurrDay => _days[_currDayNumber];
        static public List<Screening> Screenings { get; private set; }
        public List<FriendFilmRating> FriendFilmRatings { get; }
        static public List<FilmInfo> FilmInfos => _filmInfos;
        #endregion

        #region Constructors
        public ScreeningsPlan()
        {
            // Read screens.
            ListReader<Screen> ScreensReader = new ListReader<Screen>(_screensFile);
            _screens = ScreensReader.ReadListFromFile(line => new Screen(line));

            // Initialize film info.
            _filmInfos = WebUtility.LoadFilmInfoFromXml(_filmInfoFile);

            // Read films.
            ListReader<Film> FilmsReader = new ListReader<Film>(_filmsFile, true);
            _films = FilmsReader.ReadListFromFile(line => new Film(line));

            // Read friend film ratings.
            ListReader<FriendFilmRating> RatingsReader = new ListReader<FriendFilmRating>(_friendFilmRatingsFile, true);
            FriendFilmRatings = RatingsReader.ReadListFromFile(line => new FriendFilmRating(line));

            // Read screenings.
            ListReader<Screening> ScreeningsReader = new ListReader<Screening>(_screeningsFile, true);
            Screenings = ScreeningsReader.ReadListFromFile(line => new Screening(line, _screens, _films, FriendFilmRatings));

            InitializeDays();
            _currDayNumber = 0;
            _currScreenNumber = 0;
            _currScreenScreeningNumber = 0;
        }
        #endregion

        #region Private Methods
        void InitializeDays()
        {
            _days = new List<DateTime> { };
            _dayScreens = new Dictionary<DateTime, List<Screen>> { };
            _screenScreenings = new Dictionary<DateTime, Dictionary<Screen, List<Screening>>> { };

            foreach (Screening screening in Screenings)
            {
                DateTime day = screening.StartDate;
                if (!_days.Contains(day))
                {
                    _days.Add(day);
                    _dayScreens.Add(day, new List<Screen> { });
                    _screenScreenings.Add(day, new Dictionary<Screen, List<Screening>> { });
                }

                Screen screen = screening.Screen;
                if (!_dayScreens[day].Contains(screen))
                {
                    _dayScreens[day].Add(screen);
                    _screenScreenings[day].Add(screen, new List<Screening> { });
                }
                _screenScreenings[day][screen].Add(screening);
            }
            _days.Sort();
            foreach (var day in _days)
            {
                _dayScreens[day].Sort();
                foreach (var screen in _dayScreens[day])
                {
                    _screenScreenings[day][screen].Sort();
                }
            }
        }
        #endregion

        #region Public methods
        public void SetNextDay(int numberOfDays = 1)
        {
            if (NextDayExists(numberOfDays))
            {
                _currDayNumber += numberOfDays;
                _currScreenNumber = 0;
                _currScreenScreeningNumber = 0;
            }
        }

        public void SetNextScreen(int numberOfScreens = 1)
        {
            if (NextScreenWithinDayExists(numberOfScreens))
            {
                _currScreenNumber += numberOfScreens;
                _currScreenScreeningNumber = 0;
            }
        }

        public void SetNextScreening()
        {
            if (NextScreeningWithinScreenExists(1))
            {
                ++_currScreenScreeningNumber;
            }
            else
            {
                SetNextScreen(1);
            }
        }

        public void SetPrevScreening()
        {
            if (NextScreeningWithinScreenExists(-1))
            {
                --_currScreenScreeningNumber;
            }
            else
            {
                SetNextScreen(-1);
                _currScreenScreeningNumber = _screenScreenings[CurrDay][CurrScreen].Count - 1;
            }
        }

        public void SetCurrScreening(Screening screening)
        {
            SetNextDay((screening.StartDate - CurrDay).Days);
            _currScreenNumber = CurrDayScreens.IndexOf(screening.Screen);
            var screenScreenings = ScreenScreenings[CurrDay][CurrScreen];
            Screening newCurrScreening = (
                from Screening s in screenScreenings
                where s.FilmId.Equals(screening.FilmId)
                select s
            ).First();
            _currScreenScreeningNumber = screenScreenings.IndexOf(screening);
        }

        public bool NextDayExists(int numberOfDays = 1)
        {
            int nextDayNumber = _currDayNumber + numberOfDays;
            return nextDayNumber >= 0 && nextDayNumber < _days.Count;
        }

        public bool NextScreenWithinDayExists(int numberOfScreens = 1)
        {
            int nextScreenNumber = _currScreenNumber + numberOfScreens;
            return nextScreenNumber >= 0 && nextScreenNumber < _dayScreens[CurrDay].Count;
        }

        public bool NextScreeningWithinDayExists()
        {
            return NextScreeningWithinScreenExists(1) || NextScreenWithinDayExists(1);
        }

        public bool PrevScreeningWithinDayExists()
        {
            return NextScreeningWithinScreenExists(-1) || NextScreenWithinDayExists(-1);
        }

        public bool NextScreeningWithinScreenExists(int numberOfScreenings = 1)
        {
            int nextScreeningNumber = _currScreenScreeningNumber + numberOfScreenings;
            return nextScreeningNumber >= 0 && nextScreeningNumber < _screenScreenings[CurrDay][CurrScreen].Count;
        }

        public List<Screening> AttendedScreenings()
        {
            var attendedScreenings = (
                from Screening s in Screenings
                where s.IAttend || s.AttendingFriends.Count > 0
                orderby s.StartDate
                select s
            ).ToList();
            return attendedScreenings;
        }
        #endregion

        #region Debug methods
        public string DaysAsString()
        {
            string dayString = "";
            string separator = "";
            foreach (var day in _days)
            {
                dayString = dayString + separator + day.ToShortDateString();
                if (separator.Length == 0)
                {
                    separator = ", ";
                }
            }
            return dayString;
        }

        public string DayScreensAsString()
        {
            string screeningsString = "";
            string separator = "";
            foreach (var screen in _dayScreens[CurrDay])
            {
                screeningsString = screeningsString + separator + screen;
                if (separator.Length == 0)
                {
                    separator = ", ";
                }
            }
            return screeningsString;
        }
        #endregion
    }
}
