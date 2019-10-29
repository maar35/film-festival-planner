using System;
using System.Linq;
using System.Collections.Generic;
using System.Text;

namespace PresentScreenings.TableView
{
    public class ScreeningsPlanner
    {
        #region Private Members
        private List<Screening> _plannedScreenings;
        private ViewController _controller;
        private Action<string> _displayResults;
        private StringBuilder _builder = new StringBuilder("Finished planning.\n");

        #endregion

        #region Constructors
        public ScreeningsPlanner(ViewController controller, Action<string> displayResults)
        {
            _controller = controller;
            _displayResults = displayResults;
        }
        #endregion

        #region Public Methods
        public void MakeScreeningsPlan(string filmFan)
        {
            _plannedScreenings = new List<Screening> { };
            var rating = FilmRating.MaxRating;
            while (rating.IsGreaterOrEqual(FilmRating.LowestSuperRating))
            {
                // Select films with this rating.
                var films = ScreeningsPlan.Films.Where(f => ViewController.GetMaxRating(f).Equals(rating)).ToList();

                // Select free screenings of the selected films.
                var screenings = ScreeningsPlan.Screenings
                    .Where(s => IsPlannable(s, films))
                    .OrderByDescending(s => s.Status == ScreeningInfo.ScreeningStatus.AttendedByFriend)
                    .ThenByDescending(s => s.Status == ScreeningInfo.ScreeningStatus.Free)
                    .ThenByDescending(s => s.StartTime)
                    .ToList();

                // Attend the films.
                foreach (var screening in screenings)
                {
                    if (screening.IsPlannable)
                    {
                        screening.ToggleFilmFanAttendance(filmFan);
                        _controller.UpdateAttendanceStatus(screening);
                        _plannedScreenings.Add(screening);
                    }
                    _controller.ReloadScreeningsView();
                }

                // Display the results of this rating.
                DisplayResultsOfRating(rating, filmFan, films);

                // Iterate to next lower rating.
                rating.Decrease();
            }

            // Display the sceenings that were planned in this session.
            DisplayPlannedScreenings();

            // Call the display function with the result string.
            _displayResults(_builder.ToString());
        }
        #endregion

        #region Private Methods
        private bool IsPlannable(Screening screening, List<Film> films)
        {
            var inSelectedFilms = films.Count(f => f.FilmId == screening.FilmId) > 0;
            return screening.IsPlannable && inSelectedFilms;
        }

        private bool HasAttendedScreening(Film film, string filmFan)
        {
            return ViewController.FilmScreenings(film.FilmId).Any(s => s.FilmFanAttends(filmFan));
        }

        private void DisplayResultsOfRating(FilmRating rating, string filmFan, List<Film> films)
        {
            // Display summary for this rating.
            int highRatedFilmCount = films.Count;
            int plannedFilmCount = films.Where(f => HasAttendedScreening(f, filmFan)).Count();
            string fmt = "{0} out of {1} films with rating {2} planned for {3}.";
            _builder.AppendFormat(fmt, plannedFilmCount, highRatedFilmCount, rating, filmFan);

            // Display films with this rating that weren't planned.
            if (highRatedFilmCount - plannedFilmCount > 0)
            {
                string unplannedFmt = "Films with rating {0} that could not be planned for {1}:";
                _builder.AppendLine();
                _builder.AppendFormat(unplannedFmt, rating, filmFan);
                _builder.AppendLine();
                var unplannedFilms = films.Where(f => !HasAttendedScreening(f, filmFan));
                _builder.AppendJoin(Environment.NewLine, unplannedFilms);
                _builder.AppendLine();
            }
            _builder.AppendLine();
        }

        private void DisplayPlannedScreenings()
        {
            // Display newly planned screenings.
            _builder.AppendLine();
            if (_plannedScreenings.Count > 0)
            {
                _builder.AppendFormat("{0} screenings planned:", _plannedScreenings.Count);
                _builder.AppendLine();
                _plannedScreenings.Sort();
                _builder.AppendJoin(Environment.NewLine, _plannedScreenings.Select(s => s.ToPlannedScreeningString()));
            }
            else
            {
                _builder.Append("No new screenings planned.");
            }
            _builder.AppendLine();
        }
        #endregion
    }
}
