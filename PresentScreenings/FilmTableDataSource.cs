using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film table data source, provides data concerning the films displayed
    /// in the film ratings dialog,
    /// </summary>

    public class FilmTableDataSource : NSTableViewDataSource
    {
        #region Private Members
        private static AppDelegate _app;
        private static Dictionary<bool, int> _signByAscending;
        #endregion

        #region Properties
        internal List<Film> Films;
        #endregion

        #region Constructors
        public FilmTableDataSource(AppDelegate app)
        {
            _app = app;
            _signByAscending = new Dictionary<bool, int> { };
            _signByAscending[true] = 1;
            _signByAscending[false] = -1;
        }
        #endregion

        #region Override Methods
        public override nint GetRowCount(NSTableView tableView)
        {
            return Films.Count;
        }

        public override void SortDescriptorsChanged(NSTableView tableView, NSSortDescriptor[] oldDescriptors)
        {
            //base.SortDescriptorsChanged(tableView, oldDescriptors);

            //// Sort the data.
            //if (oldDescriptors.Length > 0)
            //{
            //    // Update sort.
            //    Sort(oldDescriptors[0].Key, oldDescriptors[0].Ascending);
            //}
            //else
            //{
            //    // Grab current descriptors and update sort.
            //    NSSortDescriptor[] sortDescriptor = tableView.SortDescriptors;
            //    Sort(sortDescriptor[0].Key, sortDescriptor[0].Ascending);
            //}

            // Grab current descriptors and update sort.
            NSSortDescriptor sortDescriptor = tableView.SortDescriptors.First(s => true);
            Sort(sortDescriptor.Key, sortDescriptor.Ascending);

            // Refresh table.
            tableView.ReloadData();
        }
        #endregion

        #region Public Methods
        public void Sort(string key, bool ascending)
        {
            var sign = _signByAscending[ascending];

            // Take action bases on key.
            switch (key)
            {
                case "Title":
                    Films.Sort((x, y) => sign * string.Compare(x.SortedTitle, y.SortedTitle, StringComparison.CurrentCulture));
                    break;
                case "Rating":
                    //Films.Sort((x, y) => sign * x.Rating.CompareTo(y.Rating));
                    Films.Sort((x, y) => CombinedRating(x, ascending).CompareTo(CombinedRating(y, ascending)));
                    break;
                default:
                    foreach (var friend in ScreeningInfo.MyFriends)
                    {
                        if (key == friend)
                        {
                            //Films.Sort((x, y) => sign * x.Rating.CompareTo(y.Rating));
                            break;
                        }
                    }
                    break;
            }
        }
        #endregion

        #region Private Methods
        class ratingInfo
        {
            public string Fan;
            public int Rating;
            public ratingInfo(string fan, int rating)
            {
                this.Fan = fan;
                this.Rating = rating;
            }
        }

        private static int CombinedRating(Film film, bool ascending)
        {

            var weightFactor = FilmRating.Values.Count;
            var weightedRating = 0;
            var weight = 1;
            var filmFans = new List<string>(ScreeningInfo.MyFriends);
            if (ascending)
            {
                filmFans.Insert(1, ScreeningInfo.Me);
            }
            else
            {
                filmFans.Insert(0, ScreeningInfo.Me);
            }
            filmFans.Reverse();
            var filmRatings = filmFans.Select(f => new ratingInfo(f, GetFilmFanFilmRatingToInt(film, f)));
            //if (! ascending)
            //{
            //    filmRatings.OrderByDescending(r => r.Rating);
            //}
            foreach (var rating in filmRatings.Select(r => r.Rating))
            {
                weightedRating += weight * rating;
                //}
                //foreach (var fan in filmFans)
                //{
                //weightedRating += weight * GetFilmFanFilmRatingToInt(film, fan);
                weight *= weightFactor;
            }
            return -weightedRating;
        }

        private static int GetFilmFanFilmRatingToInt(Film film, string fan = ScreeningInfo.Me)
        {
            return int.Parse(ViewController.GetFilmFanFilmRating(film, fan).ToString());
        }
        #endregion
    }
}