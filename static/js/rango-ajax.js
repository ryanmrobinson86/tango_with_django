function sync_ajax(){
  $('#likes').click(function(){
    var catid;

    catid = $(this).attr("data-catid");
    $.get('/rango/like_category/', {category_id: catid}, function(data){
      $('#cat-like-div').html(data);
      sync_ajax();
    });
  });

  $('#cat_suggestion').keyup(function(){
    var query = $(this).val();

    $.get('/rango/suggest_category/',{suggestion: query},function(data){
      $('#cats').html(data);
    });
  });

  $('.quick-add').click(function(){
    var cat_name = $(this).attr('data-cat');
    var title = $(this).attr('data-title');
    var url = $(this).attr('data-url');

    $.get('/rango/quick-add-page/',{cat: cat_name, url: url, title: title},function(data){
      $('#cat-pages').html(data);
      $(this).hide();
    });
  });
}

$(document).ready(sync_ajax());
