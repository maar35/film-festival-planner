using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

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

        #region Read Only Members
        private static readonly string HomeFolder = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
        #endregion

        #region Private Members
        private static string _directory = HomeFolder + @"/Documents/Film/IFFR/IFFR" + FestivalYear + @"/Screenings Plan";
        private static string _screensFile = Path.Combine(_directory, "screens.csv");
        private static string _filmsFile = Path.Combine(_directory, "films.csv");
        private static string _screeningsFile = Path.Combine(_directory, "screenings.csv");
        private static string _friendFilmRatingsFile = Path.Combine(_directory, "filmfanfilmratings.csv");
        private static string _filmInfoFile = Path.Combine(_directory, "filminfo.xml");
        private Dictionary<DateTime, List<Screen>> _dayScreens;
        private int _currDayNumber;
        private int _currScreenNumber;
        private int _currScreenScreeningNumber;
        #endregion

        #region Properties
        public Dictionary<DateTime, Dictionary<Screen, List<Screening>>> ScreenScreenings { get; private set; }
        public Screen CurrScreen => _dayScreens[CurrDay][_currScreenNumber];
        public Screening CurrScreening => ScreenScreenings[CurrDay][CurrScreen][_currScreenScreeningNumber];
        public List<DateTime> FestivalDays { get; private set; }
        public List<Screen> CurrDayScreens => _dayScreens[CurrDay];
        public List<Screen> Screens { get; }
        public static List<Film> Films { get; private set; }
        public DateTime CurrDay => FestivalDays[_currDayNumber];
        public static List<Screening> Screenings { get; private set; }
        public static List<FilmFanFilmRating> FilmFanFilmRatings { get; private set; }
        public static List<FilmInfo> FilmInfos { get; private set; }
        #endregion

        #region Constructors
        public ScreeningsPlan()
        {
            // Read screens.
            ListReader<Screen> ScreensReader = new ListReader<Screen>(_screensFile);
            Screens = ScreensReader.ReadListFromFile(line => new Screen(line));

            // Read film info.
            FilmInfos = FilmInfo.LoadFilmInfoFromXml(_filmInfoFile);

            // Read films.
            ListReader<Film> FilmsReader = new ListReader<Film>(_filmsFile, true);
            Films = FilmsReader.ReadListFromFile(line => new Film(line));

            // Read friend film ratings.
            ListReader<FilmFanFilmRating> RatingsReader = new ListReader<FilmFanFilmRating>(_friendFilmRatingsFile, true);
            FilmFanFilmRatings = RatingsReader.ReadListFromFile(line => new FilmFanFilmRating(line));

            // Read screenings.
            ListReader<Screening> ScreeningsReader = new ListReader<Screening>(_screeningsFile, true);
            Screenings = ScreeningsReader.ReadListFromFile(line => new Screening(line, Screens, Films, FilmFanFilmRatings));

            InitializeDays();
            _currDayNumber = 0;
            _currScreenNumber = 0;
            _currScreenScreeningNumber = 0;
        }
        #endregion

        #region Private Methods
        private void InitializeDays()
        {
            FestivalDays = new List<DateTime> { };
            _dayScreens = new Dictionary<DateTime, List<Screen>> { };
            ScreenScreenings = new Dictionary<DateTime, Dictionary<Screen, List<Screening>>> { };

            foreach (Screening screening in Screenings)
            {
                DateTime day = screening.StartDate;
                if (!FestivalDays.Contains(day))
                {
                    FestivalDays.Add(day);
                    _dayScreens.Add(day, new List<Screen> { });
                    ScreenScreenings.Add(day, new Dictionary<Screen, List<Screening>> { });
                }

                Screen screen = screening.Screen;
                if (!_dayScreens[day].Contains(screen))
                {
                    _dayScreens[day].Add(screen);
                    ScreenScreenings[day].Add(screen, new List<Screening> { });
                }
                ScreenScreenings[day][screen].Add(screening);
            }
            FestivalDays.Sort();
            foreach (var day in FestivalDays)
            {
                _dayScreens[day].Sort();
                foreach (var screen in _dayScreens[day])
                {
                    ScreenScreenings[day][screen].Sort();
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
                _currScreenScreeningNumber = ScreenScreenings[CurrDay][CurrScreen].Count - 1;
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
            return nextDayNumber >= 0 && nextDayNumber < FestivalDays.Count;
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
            return nextScreeningNumber >= 0 && nextScreeningNumber < ScreenScreenings[CurrDay][CurrScreen].Count;
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
            foreach (var day in FestivalDays)
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
