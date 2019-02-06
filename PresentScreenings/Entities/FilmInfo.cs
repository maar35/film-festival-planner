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
        public WebUtility.MediumCatagory MediumCatagory { get; }
        public string Url { get; }
        public string FilmDescription { get; }
        public string FilmArticle { get; }
        public struct ScreenedFilm
        {
            public string Title;
            public string Description;
        }
        public List<ScreenedFilm> ScreenedFilms { get; }
        #endregion

        #region Constructors
        public FilmInfo(int filmId, WebUtility.MediumCatagory catagory, string url, string description, string article)
        {
            FilmId = filmId;
            MediumCatagory = catagory;
            Url = url;
            FilmDescription = description;
            FilmArticle = article;
            ScreenedFilms = new List<ScreenedFilm> { };
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
        #endregion
    }
}
