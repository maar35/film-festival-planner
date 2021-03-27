using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml.Linq;

namespace PresentScreenings.TableView
{
    public class FilmInfo
    {
        #region Public Sub-classes.
        public class ScreenedFilm
        {
            public int ScreenedFilmId { get; }
            public string Title { get; }
            public string Description { get; }

            public ScreenedFilm(int screenedFilmId, string title, string description)
            {
                ScreenedFilmId = screenedFilmId;
                Title = title;
                Description = description;
            }

            public override string ToString()
            {
                Film film = ViewController.GetFilmById(ScreenedFilmId);
                string titleText = $"{Title} ({film.MinutesString}) - {film.MaxRating}";
                return titleText + Environment.NewLine + WebUtility.HtmlToText(Description);
            }
        }
        #endregion

        #region Properties
        public int FilmId { get; }
        public string FilmDescription { get; }
        public string FilmArticle { get; }
        public List<int> CombinationProgramIds { get; private set; }
        public List<ScreenedFilm> ScreenedFilms { get; private set; }
        public WebUtility.MediumCategory MediumCategory => ViewController.GetFilmById(FilmId).Category;
        public string Url => ViewController.GetFilmById(FilmId).Url;
        public Film.FilmInfoStatus InfoStatus { get; }
        #endregion

        #region Constructors
        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus, string description, string article)
        {
            FilmId = filmId;
            InfoStatus = infoStatus;
            FilmDescription = description;
            FilmArticle = article;
            CombinationProgramIds = new List<int> { };
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
                builder.AppendLine(WebUtility.HtmlToText(FilmDescription));
            }
            if (FilmArticle != string.Empty)
            {
                builder.AppendLine(Environment.NewLine + "Article");
                builder.AppendLine(WebUtility.HtmlToText(FilmArticle));
            }
            if (CombinationProgramIds.Count > 0)
            {
                builder.AppendLine(Environment.NewLine + "Screened as part of:");
                builder.AppendJoin(Environment.NewLine, (
                    from int filmId in CombinationProgramIds
                    select ViewController.GetFilmById(filmId)
                ));
            }
            if (ScreenedFilms.Count > 0)
            {
                builder.AppendLine(Environment.NewLine + "Screened films");
                var space = Environment.NewLine + Environment.NewLine;
                builder.AppendLine(string.Join(space, ScreenedFilms.Select(f => f.ToString())));
            }
            return builder.ToString();
        }
        #endregion

        #region Public Methods
        public void AddScreenedFilm(int filmid, string title, string description)
        {
            var screenedFilm = new ScreenedFilm(filmid, title, description);
            ScreenedFilms.Add(screenedFilm);
        }

        public static List<FilmInfo> LoadFilmInfoFromXml(string path)
        {
            var filmInfos = new List<FilmInfo> { };
            XElement root;
            try
            {
                root = XElement.Load(path);
            }
            catch (FileNotFoundException)
            {
                return filmInfos;
            }
            catch (System.Exception)
            {
                return filmInfos;
            }
            var filmInfoElements =
                from el in root.Elements("FilmInfo")
                select
                (
                    (int)el.Attribute("FilmId"),
                    (string)el.Attribute("InfoStatus"),
                    (string)el.Attribute("FilmDescription"),
                    (string)el.Attribute("FilmArticle"),
                    from c in el.Element("CombinationPrograms").Elements("CombinationProgram")
                    select
                    (
                        (int)c.Attribute("CombinationProgramId")
                    ),
                    from s in el.Element("ScreenedFilms").Elements("ScreenedFilm")
                    select
                    (
                        (string)s.Attribute("ScreenedFilmId"),
                        (string)s.Attribute("Title"),
                        (string)s.Attribute("Description")
                    )
                );
            foreach (var filmInfoElement in filmInfoElements)
            {
                var filmInfo = new FilmInfo
                (
                    filmInfoElement.Item1,
                    StringToFilmInfoStatus(filmInfoElement.Item2),
                    filmInfoElement.Item3,
                    filmInfoElement.Item4
                );
                foreach (var compilationProgramAttribute in filmInfoElement.Item5)
                {
                    filmInfo.CombinationProgramIds.Add(compilationProgramAttribute);
                }
                foreach (var screenedFilmAttribute in filmInfoElement.Item6)
                {
                    int filmid = int.Parse(screenedFilmAttribute.Item1);
                    var title = screenedFilmAttribute.Item2;
                    var description = screenedFilmAttribute.Item3;
                    filmInfo.AddScreenedFilm(filmid, title, description);
                }
                filmInfos.Add(filmInfo);
            }
            return filmInfos;
        }

        public static string InfoString(Film film)
        {
            var filmInfo = ViewController.GetFilmInfo(film.FilmId);
            if (filmInfo == null)
            {
                return string.Empty;
            }
            string text = filmInfo.FilmDescription;
            if (text.Length == 0)
            {
                text = filmInfo.FilmArticle;
            }
            return Screening.HtmlDecode(text);
        }

        public string GetGenreDescription()
        {
            Match m;
            string genrePattern = @"^Genre:(.*)$";
            m = Regex.Match(FilmArticle, genrePattern, RegexOptions.Multiline);
            if (m.Success)
            {
                return m.Result(@"$1");
            }
            return String.Empty;
        }
        #endregion

        #region Private Methods
        private static Film.FilmInfoStatus StringToFilmInfoStatus(string name)
        {
            try
            {
                return (Film.FilmInfoStatus)Enum.Parse(typeof(Film.FilmInfoStatus), name);
            }
            catch
            {
                throw new IllegalFilmInfoCategoryException($"'{name}' is not a valid FilmInfoCategory");
            }
        }

        private bool isCombinationProgram()
        {
            return MediumCategory == WebUtility.MediumCategory.CombinedProgrammes;
        }
        #endregion
    }
}
