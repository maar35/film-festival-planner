using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace PresentScreenings.TableView
{
    public class FilmInfo
    {
        #region Properties
        public int FilmId { get; }
        public Film.FilmInfoStatus InfoStatus { get; set; }
        public WebUtility.MediumCatagory MediumCatagory { get => ViewController.GetFilmById(FilmId).Catagory; }
        public string Url { get => ViewController.GetFilmById(FilmId).Url; }
        public string FilmDescription { get; private set; }
        public string FilmArticle { get; private set; }
        public struct ScreenedFilm
        {
            public string Title;
            public string Description;
        }
        public List<ScreenedFilm> ScreenedFilms { get; private set; }
        #endregion

        #region Constructors
        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus, WebUtility.MediumCatagory catagory, string url, string description, string article)
        {
            FilmId = filmId;
            InfoStatus = InfoStatus;
            //MediumCatagory = catagory;
            //Url = url;
            FilmDescription = description;
            FilmArticle = article;
            ScreenedFilms = new List<ScreenedFilm> { };
        }

        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus)
        {
            FilmId = filmId;
            InfoStatus = infoStatus;
            FilmDescription = string.Empty;
            FilmArticle = string.Empty;
            ScreenedFilms = new List<ScreenedFilm> { };
            CheckAddToFilmInfos();

            //// Temporary while moving InfoStatus from class Film to FilmInfo.
            //var film = ViewController.GetFilmById(FilmId);
            //MediumCatagory = film.Catagory;
            //Url = film.Url;
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            var builder = new StringBuilder(Url + Environment.NewLine);
            if (FilmDescription != string.Empty)
            {
                builder.AppendLine(Environment.NewLine + "Description");
                builder.AppendLine(WebUtility.HtmlToPlainText(FilmDescription));
            }
            if (FilmArticle != string.Empty)
            {
                builder.AppendLine(Environment.NewLine + "Article");
                builder.AppendLine(WebUtility.HtmlToPlainText(FilmArticle));
            }
            if (ScreenedFilms.Count > 1)
            {
                builder.AppendLine(Environment.NewLine + "Screened films");
                var space = Environment.NewLine + Environment.NewLine;
                builder.AppendLine(string.Join(space, ScreenedFilms.Select(f => f.Title + Environment.NewLine + WebUtility.HtmlToPlainText(f.Description))));
            }
            return builder.ToString();
        }
        #endregion

        #region Private Methods
        #endregion

        #region Public Methods
        public void AddScreenedFilm(string title, string description)
        {
            var screenedFilm = new ScreenedFilm();
            screenedFilm.Title = title;
            screenedFilm.Description = description;
            ScreenedFilms.Add(screenedFilm);
        }

        public void CheckAddToFilmInfos()
        {
            var filmInfos = ScreeningsPlan.FilmInfos;
            var count = filmInfos.Count(i => i.FilmId == FilmId);
            if (count > 0)
            {
                filmInfos.Remove(filmInfos.First(i => i.FilmId == FilmId));
                //filmInfos.Add(this);

                //var index = filmInfos.IndexOf(filmInfos.First(i => i.FilmId == FilmId));
                //filmInfos.ElementAt(index).InfoStatus = this.InfoStatus;
                //filmInfos.ElementAt(index).FilmDescription = this.FilmDescription;
                //filmInfos.ElementAt(index).FilmArticle = this.FilmArticle;
                //filmInfos.ElementAt(index).ScreenedFilms = this.ScreenedFilms;
            }
            filmInfos.Add(this);
        }

        public void SetFilmInfoValue(Film.FilmInfoStatus status)
        {
            InfoStatus = status;
            CheckAddToFilmInfos();
            //{
            //get => _filmInfoStatus;
            //set
            //{
            //    var filmInfo = ViewController.GetFilmInfo(FilmId);
            //    if (filmInfo != null)
            //    {
            //        filmInfo.InfoStatus = value;
            //    }
            //    else
            //    {
            //        filmInfo = new FilmInfo(FilmId, InfoStatus, Catagory, Url, string.Empty, string.Empty)
            //        {
            //            InfoStatus = value
            //        };
            //        ScreeningsPlan.FilmInfos.Add(filmInfo);
            //        //ViewController.AddFilmInfo(filmInfo);
            //    }
            //    _filmInfoStatus = filmInfo.InfoStatus;
            //}
        }
        #endregion
    }
}
