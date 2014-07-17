var f = require('fermata');

// WORKAROUND: https://github.com/natevw/fermata/issues/28
// NOTE: breaks unless run with `node --harmony_proxies`
function _apply(fn) {
    var args = Array.prototype.slice.call(arguments, 1);
    return Function.prototype.apply.call(fn, this, args);
}

function _retry() {
    var args = Array.prototype.slice.call(arguments),
        cb = args.pop(),
        fn = this;
    args.push(function (e) {
        if (e) {
            console.warn("Failed, retrying!", e.stack);
            fn.apply(null, args);
        }
        else cb.apply(this, arguments);
    });
    fn.apply(null, args);
}

var db = f.json(process.env.DB_URL);

exports.fetchPhoto = null;      // caller provides

exports.apply = _apply;
exports.retry = _retry;
exports.processPhoto = _retry.bind(function (photo, cb) {
    exports.fetchPhoto(photo, function (e,d) {
        if (e) cb(e);
        else db.post(d, function (e,d) {
            if (e) cb(e);
            else console.log(" -> saved as", d.id), cb();
        });
    });
});
