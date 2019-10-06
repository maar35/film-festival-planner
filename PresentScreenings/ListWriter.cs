using System;
using System.Collections.Generic;
using System.IO;
//using System.Reflection;

namespace PresentScreenings.TableView
{
    public class ListWriter<T> where T : ICanWriteList
    {
        #region Privat Members
        string _path;
        bool _useHeader;
        Func<string> _headerWriter;
        #endregion

        #region Constructors
        public ListWriter(string path, Func<string> THeaderWriter)
        {
            _path = path;
            _useHeader = true;
            _headerWriter = THeaderWriter;
        }
        #endregion

        #region Public Methods
        public void WriteListToFile(List<T> list)
        {
            var streamWriter = SaveStream(_path);
            if (_useHeader)
            {
                streamWriter.WriteLine(_headerWriter());
            }
            foreach (var item in list)
            {
                string line = item.Serialize();
                streamWriter.WriteLine(line);
            }
            streamWriter.Flush();
            streamWriter.Close();
        }
        #endregion

        #region Private Methods
        private StreamWriter SaveStream(string path)
        {
            FileStream fileStream;

            try
            {
                fileStream = new FileStream(path, FileMode.Create, FileAccess.Write);
            }
            catch (Exception ex)
            {
                throw new Exception(string.Format("Write error, couldn't write file {0}", path), ex);
            }

            return new StreamWriter(fileStream);
        }
        #endregion
    }
}
